/**
 * ClueAI ReviewLens — Background Service Worker
 *
 * Manifest V3 service worker.
 * Coordinates communication between popup and content scripts.
 * Step 13: stores scraped reviews per tab, generates CSV, handles downloads.
 * Step 14-1: passes degradation info from content script to popup.
 * Step 14-2: anti-crawl throttle + CAPTCHA detection + consecutive-zero tracking.
 * Step 15: direct upload to ClueAI API (POST /reviews/plugin-upload).
 *
 * Fix 2026-07-15: Use chrome.storage.session to survive service worker restarts.
 *                 Add sendMessageWithTimeout() to prevent hung Promise on dead tabs.
 * Fix #3 #4 #5 (2026-07-15): saveTabReviews propagates quota errors (#3),
 *                 per-tab serialisation lock prevents lost updates (#4),
 *                 anti-crawl state (lastScrapeTime, consecutiveZeros) persisted (#5).
 */

// ── Step 15: Marketplace TLD → code mapping ──
const MARKETPLACE_TLD_MAP = {
  '.com': 'us', '.co.uk': 'uk', '.de': 'de', '.fr': 'fr',
  '.es': 'es', '.it': 'it', '.co.jp': 'jp', '.ca': 'ca',
  '.in': 'in', '.com.au': 'au', '.com.br': 'br', '.com.mx': 'mx',
  '.nl': 'nl', '.se': 'se', '.pl': 'pl', '.sg': 'sg',
  '.ae': 'ae', '.sa': 'sa', '.tr': 'tr',
};

/**
 * Resolve the ClueAI API base URL.
 * Reads an override from storage (used in local dev), defaults to production.
 */
async function getApiBaseUrl() {
  const DEFAULT = 'https://api.clueai-reviewlens.com';
  try {
    const storage = await chrome.storage.local.get('apiBaseUrl');
    if (storage.apiBaseUrl) return storage.apiBaseUrl;
  } catch (_) { /* use default */ }
  return DEFAULT;
}

/**
 * Extract ASIN from an Amazon URL.
 * Supports /dp/<ASIN> and /product-reviews/<ASIN> patterns.
 */
function extractAsin(url) {
  if (!url) return null;
  // /dp/B0XXXXXXX
  let m = url.match(/\/dp\/([A-Z0-9]{10})/i);
  if (m) return m[1];
  // /product-reviews/B0XXXXXXX
  m = url.match(/\/product-reviews\/([A-Z0-9]{10})/i);
  if (m) return m[1];
  return null;
}

/**
 * Detect marketplace code from an Amazon URL hostname.
 * e.g. www.amazon.com → us, www.amazon.co.uk → uk
 */
function detectMarketplace(url) {
  if (!url) return 'us';
  try {
    const hostname = new URL(url).hostname;
    // Match the longest TLD suffix first (e.g. .co.uk before .uk)
    const suffixes = Object.keys(MARKETPLACE_TLD_MAP).sort((a, b) => b.length - a.length);
    for (const suffix of suffixes) {
      if (hostname.endsWith(suffix)) {
        return MARKETPLACE_TLD_MAP[suffix];
      }
    }
  } catch (_) { /* fall through */ }
  return 'us'; // default
}

// ── In-memory cache (lost on SW restart; non-critical page info) ──
const tabPageInfo = new Map();

// ── Step 14-2: Anti-crawl rate limiting ──
/** Minimum interval (ms) between two scrapes on the same tab */
const MIN_SCRAPE_INTERVAL_MS = 3000;
// Anti-crawl state (lastScrapeTime, consecutiveZeros) persisted via loadTabMeta/saveTabMeta (#5)

// ── Fix 2026-07-15: Timeout wrapper for chrome.tabs.sendMessage ──
/**
 * Send a message to a tab's content script with a timeout.
 * Resolves with the response, or rejects after timeoutMs.
 * @param {number} tabId
 * @param {object} message
 * @param {number} [timeoutMs=15000]
 */
function sendMessageWithTimeout(tabId, message, timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`sendMessage timeout after ${timeoutMs}ms (type=${message.type})`));
    }, timeoutMs);

    chrome.tabs.sendMessage(tabId, message, (response) => {
      clearTimeout(timer);
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(response);
      }
    });
  });
}

// ── Fix 2026-07-15: Storage helpers for tabReviews (persists across SW restart) ──
/**
 * Load stored reviews for a tab from chrome.storage.session.
 * Returns { reviews: [], seenIds: Set } or null.
 */
async function loadTabReviews(tabId) {
  try {
    const key = `tabReviews_${tabId}`;
    const result = await chrome.storage.session.get(key);
    const data = result[key];
    if (!data) return null;
    return {
      reviews: data.reviews || [],
      seenIds: new Set(data.seenIds || []),
    };
  } catch (_) {
    return null;
  }
}

/**
 * Save reviews for a tab to chrome.storage.session.
 * seenIds is serialised as array for JSON compatibility.
 */
async function saveTabReviews(tabId, stored) {
  try {
    const key = `tabReviews_${tabId}`;
    await chrome.storage.session.set({
      [key]: {
        reviews: stored.reviews,
        seenIds: Array.from(stored.seenIds),
      },
    });
  } catch (err) {
    console.warn('[ReviewLens BG] Failed to persist tabReviews:', err);
    // Fix #3: propagate quota / storage errors so popup can warn the user
    return { ok: false, error: err?.message?.includes('QUOTA') ? 'quota_exceeded' : 'storage_error' };
  }
  return { ok: true };
}

/**
 * Delete stored reviews for a tab from chrome.storage.session.
 */
async function deleteTabReviews(tabId) {
  try {
    await chrome.storage.session.remove(`tabReviews_${tabId}`);
  } catch (_) { /* ignore */ }
}

// ── Fix #4 (2026-07-15): Per-tab serialisation lock ──
// Prevents lost updates when read→mutate→write runs concurrently for the same tab.
// The popup serialises scrapes via the isScraping flag, and STORE_REVIEWS is a
// reserved handler with no callers today — so contention is nil in practice.
// The lock is belt-and-suspenders for correctness under future concurrent use.
const tabLocks = new Map();

/**
 * Serialise async operations on the same tab to prevent lost updates.
 * @param {number} tabId
 * @param {() => Promise<any>} fn
 * @returns {Promise<any>} resolves with fn()'s return value
 */
async function withTabLock(tabId, fn) {
  const prev = tabLocks.get(tabId) || Promise.resolve();
  let release;
  const next = new Promise(resolve => { release = resolve; });
  tabLocks.set(tabId, next);
  try {
    await prev;
    return await fn();
  } finally {
    release();
  }
}

// ── Fix #5 (2026-07-15): Persist anti-crawl state to survive SW restarts ──
// tabLastScrapeTime and tabConsecutiveZeros were in-memory Maps, lost on restart.
// Now persisted in chrome.storage.session, same as tabReviews.

/**
 * Load anti-crawl metadata for a tab from storage.session.
 * @returns {{ lastScrapeTime: number, consecutiveZeros: number }}
 */
async function loadTabMeta(tabId) {
  try {
    const key = `tabMeta_${tabId}`;
    const result = await chrome.storage.session.get(key);
    return result[key] || { lastScrapeTime: 0, consecutiveZeros: 0 };
  } catch (_) {
    return { lastScrapeTime: 0, consecutiveZeros: 0 };
  }
}

/**
 * Persist anti-crawl metadata for a tab to storage.session.
 */
async function saveTabMeta(tabId, meta) {
  try {
    const key = `tabMeta_${tabId}`;
    await chrome.storage.session.set({ [key]: meta });
  } catch (err) {
    console.warn('[ReviewLens BG] Failed to persist tabMeta:', err);
  }
}

/**
 * Delete anti-crawl metadata for a tab from storage.session.
 */
async function deleteTabMeta(tabId) {
  try {
    await chrome.storage.session.remove(`tabMeta_${tabId}`);
  } catch (_) { /* ignore */ }
}

/**
 * Listen for messages from content scripts and popup
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    // ── Content script: page type detected on load ──
    case 'PAGE_TYPE_DETECTED': {
      const tabId = sender.tab?.id;
      if (tabId != null) {
        tabPageInfo.set(tabId, {
          pageType: message.pageType,
          url: message.url,
          timestamp: Date.now(),
        });
      }
      sendResponse({ received: true });
      break;
    }

    // ── Popup: query page info for active tab ──
    case 'GET_PAGE_INFO': {
      (async () => {
        try {
          const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true,
          });
          if (!tab || !tab.id) {
            sendResponse({ pageType: 'unknown', url: null });
            return;
          }

          // Try cached info first, fall back to URL-based detection
          const cached = tabPageInfo.get(tab.id);
          if (cached && cached.url === tab.url) {
            sendResponse({
              pageType: cached.pageType,
              url: cached.url,
              source: 'content_script',
              degradation: cached.degradation || null,
            });
            return;
          }

          // Fallback: detect from tab URL
          sendResponse({
            pageType: detectPageTypeFromUrl(tab.url || ''),
            url: tab.url || '',
            source: 'url_fallback',
            degradation: null,
          });
        } catch (err) {
          console.error('[ReviewLens BG] Error getting page info:', err);
          sendResponse({ pageType: 'error', url: null, error: String(err) });
        }
      })();
      return true; // keep channel open for async sendResponse
    }

    // ── Step 11: forward EXTRACT_REVIEWS to content script ──
    case 'EXTRACT_REVIEWS': {
      (async () => {
        try {
          const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true,
          });
          if (!tab || !tab.id) {
            sendResponse({
              reviews: [],
              stats: { total_found: 0, total_extracted: 0, error: 'no_active_tab' },
            });
            return;
          }

          // Forward to content script with timeout
          const result = await sendMessageWithTimeout(tab.id, {
            type: 'EXTRACT_REVIEWS',
          });
          sendResponse(result);
        } catch (err) {
          console.error('[ReviewLens BG] Error forwarding EXTRACT_REVIEWS:', err);
          sendResponse({
            reviews: [],
            stats: { total_found: 0, total_extracted: 0, error: String(err) },
          });
        }
      })();
      return true; // keep channel open for async sendResponse
    }

    // ── Step 13: Start scraping + accumulate reviews ──
    // Step 14-2: throttle + CAPTCHA + consecutive-zero tracking
    // Fix #3 #4 #5 (2026-07-15): lock serialises, anti-crawl state persisted, quota errors propagated
    case 'START_SCRAPING': {
      (async () => {
        try {
          const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true,
          });
          if (!tab || !tab.id) {
            sendResponse({ success: false, error: 'no_active_tab' });
            return;
          }

          // ── Fix #4: Serialise the entire scrape flow per tab ──
          const result = await withTabLock(tab.id, async () => {

          // ── Fix #5: Load anti-crawl state from storage.session ──
          const meta = await loadTabMeta(tab.id);

          // ── Step 14-2: Throttle check ──
          const now = Date.now();
          const elapsed = now - meta.lastScrapeTime;
          if (elapsed < MIN_SCRAPE_INTERVAL_MS) {
            const stored = await loadTabReviews(tab.id);
            return {
              success: false,
              throttled: true,
              wait_ms: MIN_SCRAPE_INTERVAL_MS - elapsed,
              total_reviews: stored?.reviews?.length || 0,
            };
          }

          // ── Step 14-2: Pre-check CAPTCHA before scraping ──
          try {
            const captchaCheck = await sendMessageWithTimeout(tab.id, {
              type: 'DETECT_CAPTCHA',
            }, 5000);
            if (captchaCheck?.captcha_detected) {
              // Update last scrape time even for CAPTCHA (avoids hammering)
              meta.lastScrapeTime = now;
              await saveTabMeta(tab.id, meta);
              const stored = await loadTabReviews(tab.id);
              return {
                success: false,
                captcha_detected: true,
                total_reviews: stored?.reviews?.length || 0,
                stats: {
                  captcha_detected: true,
                  degraded: true,
                  degrade_reason: 'captcha',
                  degrade_detail:
                    'Amazon CAPTCHA / Robot Check 页面检测到验证码，无法自动抓取。',
                },
              };
            }
          } catch (_) {
            // Content script may not be injected; proceed anyway
          }

          // Trigger extraction in content script (with timeout)
          let extraction;
          try {
            extraction = await sendMessageWithTimeout(tab.id, {
              type: 'EXTRACT_REVIEWS',
            }, 20000);
          } catch (timeoutErr) {
            console.warn('[ReviewLens BG] EXTRACT_REVIEWS timed out:', timeoutErr.message);
            return {
              success: false,
              error: 'content_script_timeout',
              error_message: '页面响应超时，请刷新页面后重试。',
            };
          }

          // ── Step 14-2: Update anti-crawl state (#5: to storage.session) ──
          meta.lastScrapeTime = Date.now();
          const reviewCount = extraction?.reviews?.length || 0;
          if (reviewCount === 0) {
            meta.consecutiveZeros = (meta.consecutiveZeros || 0) + 1;
          } else {
            meta.consecutiveZeros = 0;
          }
          await saveTabMeta(tab.id, meta);

          // Check for CAPTCHA in extraction result (fallback)
          const captchaInResult = extraction?.stats?.captcha_detected || false;

          // Accumulate reviews in persistent storage (dedup by review_id)
          if (extraction && extraction.reviews && extraction.reviews.length > 0) {
            const stored = (await loadTabReviews(tab.id)) || { reviews: [], seenIds: new Set() };
            let newCount = 0;
            for (const review of extraction.reviews) {
              if (!stored.seenIds.has(review.review_id)) {
                stored.seenIds.add(review.review_id);
                stored.reviews.push(review);
                newCount++;
              }
            }
            const saveResult = await saveTabReviews(tab.id, stored);

            // Update page info with review count
            const pageInfo = tabPageInfo.get(tab.id) || {};
            tabPageInfo.set(tab.id, {
              ...pageInfo,
              reviewCount: stored.reviews.length,
              lastExtraction: Date.now(),
            });

            // Step 14-1: store degradation info so popup can show it proactively
            if (extraction?.stats?.degraded) {
              const pageInfo2 = tabPageInfo.get(tab.id) || {};
              tabPageInfo.set(tab.id, {
                ...pageInfo2,
                degradation: {
                  degraded: true,
                  degrade_reason: extraction.stats.degrade_reason,
                  degrade_detail: extraction.stats.degrade_detail,
                  page_type: extraction.stats.page_type,
                  timestamp: Date.now(),
                },
              });
            } else {
              // Clear degradation if extraction succeeded
              const pageInfo2 = tabPageInfo.get(tab.id);
              if (pageInfo2?.degradation) {
                tabPageInfo.set(tab.id, { ...pageInfo2, degradation: null });
              }
            }

            return {
              success: true,
              new_reviews: newCount,
              total_reviews: stored.reviews.length,
              stats: extraction.stats,
              captcha_detected: captchaInResult,
              consecutive_zeros: meta.consecutiveZeros,
              // Fix #3: propagate storage errors so popup can warn
              storage_error: saveResult.ok ? undefined : saveResult.error,
            };
          }

            // No new reviews — still track degradation
            if (extraction?.stats?.degraded) {
              const pageInfo = tabPageInfo.get(tab.id) || {};
              tabPageInfo.set(tab.id, {
                ...pageInfo,
                degradation: {
                  degraded: true,
                  degrade_reason: extraction.stats.degrade_reason,
                  degrade_detail: extraction.stats.degrade_detail,
                  page_type: extraction.stats.page_type,
                  timestamp: Date.now(),
                },
              });
            }

            const stored = await loadTabReviews(tab.id);
            return {
              success: true,
              new_reviews: 0,
              total_reviews: stored?.reviews?.length || 0,
              stats: extraction?.stats || null,
              captcha_detected: captchaInResult,
              consecutive_zeros: meta.consecutiveZeros,
            };
          }); // end withTabLock

          sendResponse(result);
        } catch (err) {
          console.error('[ReviewLens BG] Error in START_SCRAPING:', err);
          sendResponse({ success: false, error: String(err) });
        }
      })();
      return true;
    }

    // ── Step 13: Get current scrape status for popup ──
    case 'GET_SCRAPE_STATUS': {
      (async () => {
        try {
          const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true,
          });
          if (!tab || !tab.id) {
            sendResponse({ total_reviews: 0, page_info: null });
            return;
          }

          const stored = await loadTabReviews(tab.id);
          const pageInfo = tabPageInfo.get(tab.id);

          // Step 14-2: Include throttle + zero-count info (#5: from storage.session)
          const meta = await loadTabMeta(tab.id);
          const now = Date.now();
          const elapsed = now - meta.lastScrapeTime;
          const throttled = elapsed < MIN_SCRAPE_INTERVAL_MS;
          const throttleWaitMs = throttled ? MIN_SCRAPE_INTERVAL_MS - elapsed : 0;

          sendResponse({
            total_reviews: stored ? stored.reviews.length : 0,
            reviews: stored ? stored.reviews : [],
            page_info: pageInfo || null,
            throttled: throttled,
            throttle_wait_ms: throttleWaitMs,
            consecutive_zeros: meta.consecutiveZeros,
          });
        } catch (err) {
          console.error('[ReviewLens BG] Error in GET_SCRAPE_STATUS:', err);
          sendResponse({ total_reviews: 0, reviews: [], page_info: null, error: String(err) });
        }
      })();
      return true;
    }

    // ── Step 13: Export reviews as CSV ──
    case 'EXPORT_CSV': {
      (async () => {
        try {
          const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true,
          });
          if (!tab || !tab.id) {
            sendResponse({ success: false, error: 'no_active_tab' });
            return;
          }

          const stored = await loadTabReviews(tab.id);
          if (!stored || stored.reviews.length === 0) {
            sendResponse({ success: false, error: 'no_reviews' });
            return;
          }

          const csvContent = generateCsv(stored.reviews);
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
          const filename = `clueai-reviews-${timestamp}.csv`;

          // Encode CSV with BOM for Excel compatibility
          const csvWithBOM = '﻿' + csvContent;
          const dataUrl = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvWithBOM);

          try {
            await chrome.downloads.download({
              url: dataUrl,
              filename: filename,
              saveAs: true,
            });
            sendResponse({
              success: true,
              filename: filename,
              total_exported: stored.reviews.length,
            });
          } catch (downloadErr) {
            // Fallback: try base64 encoding for large payloads
            console.warn('[ReviewLens BG] Direct encoding failed, trying base64:', downloadErr);
            const base64 = btoa(unescape(encodeURIComponent(csvWithBOM)));
            const base64Url = 'data:text/csv;charset=utf-8;base64,' + base64;
            await chrome.downloads.download({
              url: base64Url,
              filename: filename,
              saveAs: true,
            });
            sendResponse({
              success: true,
              filename: filename,
              total_exported: stored.reviews.length,
            });
          }
        } catch (err) {
          console.error('[ReviewLens BG] Error in EXPORT_CSV:', err);
          sendResponse({ success: false, error: String(err) });
        }
      })();
      return true;
    }

    // ── Step 15: Upload reviews directly to ClueAI API ──
    case 'UPLOAD_TO_API': {
      (async () => {
        try {
          const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true,
          });
          if (!tab || !tab.id) {
            sendResponse({ success: false, error: 'no_active_tab' });
            return;
          }

          const stored = await loadTabReviews(tab.id);
          if (!stored || stored.reviews.length === 0) {
            sendResponse({ success: false, error: 'no_reviews' });
            return;
          }

          const asin = extractAsin(tab.url);
          const marketplace = detectMarketplace(tab.url);

          // Read API base URL (storage override in dev, else production)
          const apiBaseUrl = await getApiBaseUrl();

          // Build request body
          const requestBody = {
            asin: asin || '',
            marketplace: marketplace,
            platform: 'amazon',
            product_name: null,
            page_url: tab.url || '',
            reviews: stored.reviews.map((r) => ({
              review_id: r.review_id || '',
              body: r.body || '',
              rating: typeof r.rating === 'number' ? r.rating : null,
              date: r.date || null,
              reviewer: r.reviewer || null,
              title: r.title || null,
              verified: !!r.verified,
              helpful_count: typeof r.helpful_count === 'number' ? r.helpful_count : null,
            })),
          };

          const response = await fetch(apiBaseUrl + '/reviews/plugin-upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(requestBody),
          });

          if (response.status === 401) {
            sendResponse({
              success: false,
              error: 'needs_login',
              message: '请先登录 ClueAI',
            });
            return;
          }

          if (!response.ok) {
            const errorText = await response.text().catch(() => '');
            sendResponse({
              success: false,
              error: 'api_error',
              message: 'API 返回错误 (' + response.status + '): ' + errorText.slice(0, 200),
            });
            return;
          }

          const result = await response.json();

          // Clear stored reviews on successful upload
          await deleteTabReviews(tab.id);
          const pageInfo = tabPageInfo.get(tab.id) || {};
          tabPageInfo.set(tab.id, { ...pageInfo, reviewCount: 0 });

          // Step 14-2: also reset throttle/zero counters for this tab (#5: from storage.session)
          await deleteTabMeta(tab.id);

          sendResponse({
            success: true,
            ok: result.ok,
            job_id: result.job_id,
            asin: result.asin,
            marketplace: result.marketplace,
            total_received: result.total_received,
            new_reviews: result.new_reviews,
            duplicate_count: result.duplicate_count,
            message: result.message,
          });
        } catch (err) {
          console.error('[ReviewLens BG] Upload error:', err);
          sendResponse({
            success: false,
            error: 'network_error',
            message: '网络错误：' + (err.message || '无法连接到服务器'),
          });
        }
      })();
      return true;
    }

    // ── Step 16: Check ClueAI login state via cookie passthrough (GET /me) ──
    // Auth is cookie-based (httponly session cookie on api.clueai-reviewlens.com).
    // credentials:'include' sends that cookie, so a logged-in web session is
    // reused by the extension with no separate token handling.
    case 'CHECK_LOGIN': {
      (async () => {
        try {
          const apiBaseUrl = await getApiBaseUrl();
          const response = await fetch(apiBaseUrl + '/me', {
            method: 'GET',
            headers: { Accept: 'application/json' },
            credentials: 'include',
          });

          if (response.status === 401) {
            sendResponse({ success: true, logged_in: false });
            return;
          }
          if (!response.ok) {
            sendResponse({
              success: false,
              logged_in: false,
              error: 'api_error',
              status: response.status,
            });
            return;
          }

          const user = await response.json();
          sendResponse({
            success: true,
            logged_in: true,
            username: user.username || '',
            plan: user.plan || null,
          });
        } catch (err) {
          console.error('[ReviewLens BG] CHECK_LOGIN error:', err);
          // Network failure is not "logged out" — report distinctly so the
          // popup can avoid a misleading "not signed in" message.
          sendResponse({
            success: false,
            logged_in: false,
            error: 'network_error',
            message: String(err && err.message ? err.message : err),
          });
        }
      })();
      return true;
    }

    // ── Step 13: Clear stored reviews for a tab ──
    case 'CLEAR_REVIEWS': {
      (async () => {
        try {
          const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true,
          });
          if (tab && tab.id) {
            await deleteTabReviews(tab.id);
            const pageInfo = tabPageInfo.get(tab.id) || {};
            tabPageInfo.set(tab.id, { ...pageInfo, reviewCount: 0 });
          }
          sendResponse({ success: true });
        } catch (err) {
          console.error('[ReviewLens BG] Error in CLEAR_REVIEWS:', err);
          sendResponse({ success: false, error: String(err) });
        }
      })();
      return true;
    }

    // ── Step 13: Store reviews data sent from content script ──
    // Fix #4: serialised via per-tab lock (currently no concurrent callers; belt-and-suspenders)
    case 'STORE_REVIEWS': {
      const tabId = sender.tab?.id;
      if (tabId != null && message.reviews && message.reviews.length > 0) {
        withTabLock(tabId, async () => {
          const stored = (await loadTabReviews(tabId)) || { reviews: [], seenIds: new Set() };
          let newCount = 0;
          for (const review of message.reviews) {
            if (!stored.seenIds.has(review.review_id)) {
              stored.seenIds.add(review.review_id);
              stored.reviews.push(review);
              newCount++;
            }
          }
          await saveTabReviews(tabId, stored);

          const pageInfo = tabPageInfo.get(tabId) || {};
          tabPageInfo.set(tabId, {
            ...pageInfo,
            reviewCount: stored.reviews.length,
            lastExtraction: Date.now(),
          });

          console.log(
            '[ReviewLens BG] Stored reviews: +' + newCount +
            ', total=' + stored.reviews.length + ', tabId=' + tabId
          );
          sendResponse({ received: true });
        }).catch((err) => {
          console.error('[ReviewLens BG] STORE_REVIEWS error:', err);
          sendResponse({ received: false, error: String(err) });
        });
        return true;
      }
      sendResponse({ received: true });
      break;
    }

    // ── Step 12: pagination result forwarded from content script ──
    case 'EXTRACT_REVIEWS_RESULT': {
      const tabId = sender.tab?.id;
      console.log(
        '[ReviewLens BG] 分页提取结果: tabId=' + tabId +
        ', count=' + message.count +
        ', total=' + message.total +
        ', url=' + message.url
      );
      // Store review count for future popup queries
      if (tabId != null) {
        const existing = tabPageInfo.get(tabId) || {};
        tabPageInfo.set(tabId, {
          ...existing,
          reviewCount: message.total,
          lastExtraction: message.timestamp,
        });
      }
      sendResponse({ received: true });
      break;
    }

    default: {
      sendResponse({ received: false, error: `Unknown message type: ${message.type}` });
      break;
    }
  }
});

/**
 * Detect Amazon page type from URL string
 */
function detectPageTypeFromUrl(url) {
  if (!url) return 'unknown';

  // Not Amazon
  if (!/amazon\./.test(url)) {
    return 'not_amazon';
  }

  // Product page: /dp/<ASIN>
  if (/\/dp\/[A-Z0-9]{10}/i.test(url)) {
    return 'product';
  }

  // Review page: /product-reviews/<ASIN>
  if (/\/product-reviews\//i.test(url)) {
    return 'reviews';
  }

  return 'amazon_other';
}

// ── CSV Generation (Step 13) ──

/**
 * Generate CSV content from review objects.
 * Columns match the existing upload template format.
 */
function generateCsv(reviews) {
  const headers = [
    'review_id',
    'body',
    'rating',
    'date',
    'date_iso',
    'reviewer',
    'title',
    'verified',
    'helpful_count',
    'marketplace',
    'scraped_at',
    'page_url',
  ];

  const rows = [headers.join(',')];

  for (const review of reviews) {
    const row = headers.map((h) => escapeCsvField(review[h]));
    rows.push(row.join(','));
  }

  return rows.join('\n');
}

/**
 * Escape a value for CSV output.
 * Wraps in quotes if value contains comma, quote, or newline.
 * Doubles internal quotes per RFC 4180.
 */
function escapeCsvField(value) {
  if (value == null) return '';

  const str = String(value);

  // Check if escaping is needed
  if (
    str.includes(',') ||
    str.includes('"') ||
    str.includes('\n') ||
    str.includes('\r')
  ) {
    return '"' + str.replace(/"/g, '""') + '"';
  }

  return str;
}

// Clean up stale tab info when tabs close
chrome.tabs.onRemoved.addListener((tabId) => {
  tabPageInfo.delete(tabId);
  deleteTabMeta(tabId);    // Fix #5 (2026-07-15): clean anti-crawl state from storage.session
  tabLocks.delete(tabId);  // Fix #4 (2026-07-15): clean serialisation lock
  deleteTabReviews(tabId); // Fix 2026-07-15: clean reviews from storage.session
});

console.log('[ReviewLens BG] Service worker registered — v16 fix-#3-quota-#4-lock-#5-anticrawl-persist');
