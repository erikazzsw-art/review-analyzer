/**
 * ClueAI ReviewLens — Background Service Worker
 *
 * Manifest V3 service worker.
 * Coordinates communication between popup and content scripts.
 * Step 13: stores scraped reviews per tab, generates CSV, handles downloads.
 * Step 14-1: passes degradation info from content script to popup.
 * Step 14-2: anti-crawl throttle + CAPTCHA detection + consecutive-zero tracking.
 */

// Store the latest page info reported by content scripts, keyed by tabId
const tabPageInfo = new Map();

// Store accumulated reviews keyed by tabId (Step 13)
const tabReviews = new Map();

// ── Step 14-2: Anti-crawl rate limiting ──
/** Minimum interval (ms) between two scrapes on the same tab */
const MIN_SCRAPE_INTERVAL_MS = 3000;
/** Timestamp of last scrape per tab */
const tabLastScrapeTime = new Map();
/** Consecutive zero-result scrape count per tab */
const tabConsecutiveZeros = new Map();

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

          // Forward to content script in the active tab
          const result = await chrome.tabs.sendMessage(tab.id, {
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

          // ── Step 14-2: Throttle check ──
          const now = Date.now();
          const lastTime = tabLastScrapeTime.get(tab.id) || 0;
          const elapsed = now - lastTime;
          if (elapsed < MIN_SCRAPE_INTERVAL_MS) {
            sendResponse({
              success: false,
              throttled: true,
              wait_ms: MIN_SCRAPE_INTERVAL_MS - elapsed,
              total_reviews: (tabReviews.get(tab.id) || {}).reviews?.length || 0,
            });
            return;
          }

          // ── Step 14-2: Pre-check CAPTCHA before scraping ──
          try {
            const captchaCheck = await chrome.tabs.sendMessage(tab.id, {
              type: 'DETECT_CAPTCHA',
            });
            if (captchaCheck?.captcha_detected) {
              // Update last scrape time even for CAPTCHA (avoids hammering)
              tabLastScrapeTime.set(tab.id, now);
              sendResponse({
                success: false,
                captcha_detected: true,
                total_reviews: (tabReviews.get(tab.id) || {}).reviews?.length || 0,
                stats: {
                  captcha_detected: true,
                  degraded: true,
                  degrade_reason: 'captcha',
                  degrade_detail:
                    'Amazon CAPTCHA / Robot Check 页面检测到验证码，无法自动抓取。',
                },
              });
              return;
            }
          } catch (_) {
            // Content script may not be injected; proceed anyway
          }

          // Trigger extraction in content script
          const result = await chrome.tabs.sendMessage(tab.id, {
            type: 'EXTRACT_REVIEWS',
          });

          // ── Step 14-2: Update last scrape time ──
          tabLastScrapeTime.set(tab.id, Date.now());

          // ── Step 14-2: Track consecutive zeros ──
          const reviewCount = result?.reviews?.length || 0;
          if (reviewCount === 0) {
            const zeros = (tabConsecutiveZeros.get(tab.id) || 0) + 1;
            tabConsecutiveZeros.set(tab.id, zeros);
          } else {
            tabConsecutiveZeros.set(tab.id, 0);
          }
          const consecutiveZeros = tabConsecutiveZeros.get(tab.id) || 0;

          // Check for CAPTCHA in extraction result (fallback)
          const captchaDetected = result?.stats?.captcha_detected || false;

          // Accumulate reviews in tab storage (dedup by review_id)
          if (result && result.reviews && result.reviews.length > 0) {
            const stored = tabReviews.get(tab.id) || { reviews: [], seenIds: new Set() };
            let newCount = 0;
            for (const review of result.reviews) {
              if (!stored.seenIds.has(review.review_id)) {
                stored.seenIds.add(review.review_id);
                stored.reviews.push(review);
                newCount++;
              }
            }
            tabReviews.set(tab.id, stored);

            // Update page info with review count
            const pageInfo = tabPageInfo.get(tab.id) || {};
            tabPageInfo.set(tab.id, {
              ...pageInfo,
              reviewCount: stored.reviews.length,
              lastExtraction: Date.now(),
            });

            // Step 14-1: store degradation info so popup can show it proactively
            if (result?.stats?.degraded) {
              const pageInfo = tabPageInfo.get(tab.id) || {};
              tabPageInfo.set(tab.id, {
                ...pageInfo,
                degradation: {
                  degraded: true,
                  degrade_reason: result.stats.degrade_reason,
                  degrade_detail: result.stats.degrade_detail,
                  page_type: result.stats.page_type,
                  timestamp: Date.now(),
                },
              });
            } else {
              // Clear degradation if extraction succeeded
              const pageInfo = tabPageInfo.get(tab.id);
              if (pageInfo?.degradation) {
                tabPageInfo.set(tab.id, { ...pageInfo, degradation: null });
              }
            }

            sendResponse({
              success: true,
              new_reviews: newCount,
              total_reviews: stored.reviews.length,
              stats: result.stats,
              captcha_detected: captchaDetected,
              consecutive_zeros: consecutiveZeros,
            });
          } else {
            // Step 14-1: store degradation info even when no new reviews
            if (result?.stats?.degraded) {
              const pageInfo = tabPageInfo.get(tab.id) || {};
              tabPageInfo.set(tab.id, {
                ...pageInfo,
                degradation: {
                  degraded: true,
                  degrade_reason: result.stats.degrade_reason,
                  degrade_detail: result.stats.degrade_detail,
                  page_type: result.stats.page_type,
                  timestamp: Date.now(),
                },
              });
            }

            sendResponse({
              success: true,
              new_reviews: 0,
              total_reviews: (tabReviews.get(tab.id) || {}).reviews?.length || 0,
              stats: result?.stats || null,
              captcha_detected: captchaDetected,
              consecutive_zeros: consecutiveZeros,
            });
          }
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

          const stored = tabReviews.get(tab.id);
          const pageInfo = tabPageInfo.get(tab.id);

          // Step 14-2: Include throttle + zero-count info
          const now = Date.now();
          const lastTime = tabLastScrapeTime.get(tab.id) || 0;
          const elapsed = now - lastTime;
          const throttled = elapsed < MIN_SCRAPE_INTERVAL_MS;
          const throttleWaitMs = throttled ? MIN_SCRAPE_INTERVAL_MS - elapsed : 0;

          sendResponse({
            total_reviews: stored ? stored.reviews.length : 0,
            reviews: stored ? stored.reviews : [],
            page_info: pageInfo || null,
            // Step 14-2
            throttled: throttled,
            throttle_wait_ms: throttleWaitMs,
            consecutive_zeros: tabConsecutiveZeros.get(tab.id) || 0,
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

          const stored = tabReviews.get(tab.id);
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

    // ── Step 13: Clear stored reviews for a tab ──
    case 'CLEAR_REVIEWS': {
      (async () => {
        try {
          const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true,
          });
          if (tab && tab.id) {
            tabReviews.delete(tab.id);
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
    case 'STORE_REVIEWS': {
      const tabId = sender.tab?.id;
      if (tabId != null && message.reviews && message.reviews.length > 0) {
        const stored = tabReviews.get(tabId) || { reviews: [], seenIds: new Set() };
        let newCount = 0;
        for (const review of message.reviews) {
          if (!stored.seenIds.has(review.review_id)) {
            stored.seenIds.add(review.review_id);
            stored.reviews.push(review);
            newCount++;
          }
        }
        tabReviews.set(tabId, stored);

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
  tabReviews.delete(tabId);
  tabLastScrapeTime.delete(tabId);   // Step 14-2
  tabConsecutiveZeros.delete(tabId); // Step 14-2
});

console.log('[ReviewLens BG] Service worker registered — v14.2 throttle+CAPTCHA active');
