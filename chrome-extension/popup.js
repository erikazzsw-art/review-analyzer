/**
 * ClueAI ReviewLens — Popup Script
 *
 * Step 13: One-click review scraping, progress display, CSV export.
 * Step 14-1: Degradation detection UI — shows page structure change warnings.
 * Step 14-2: Anti-crawl — CAPTCHA detection, throttle countdown, consecutive-zero warnings.
 * Step 15: direct upload to ClueAI API (POST /reviews/plugin-upload).
 * Step 16: bilingual UI (zh/en) via I18N + language toggle; login-state check
 *          via cookie passthrough (GET /me). All user-facing strings go through
 *          I18N.t() so the language toggle re-renders them live.
 * Communicates with background service worker for all operations.
 */

// Short alias for the global i18n helper (loaded via i18n.js before this file).
const t = (key, params) => (typeof I18N !== 'undefined' ? I18N.t(key, params) : key);

// ── Module-scope state ──
// Fix 2026-07-15: throttleTimer / currentPageInfo MUST live at module scope.
// The anti-crawl helpers (hideAntiCrawlUI / startThrottleCountdown) are defined
// at module scope below; if these vars were declared inside DOMContentLoaded
// those helpers would throw `ReferenceError: throttleTimer is not defined`.
// That threw synchronously at the top of the scrape click handler (before its
// try/finally), so isScraping stayed true and the button hung on "抓取中…"
// forever — the real cause of the永久卡死 bug (not the SW-restart theory).
let throttleTimer = null; // Step 14-2: countdown interval ref
let currentPageInfo = null;
let lastLoginState = null; // Step 16: cache last /me result for re-render on lang toggle

document.addEventListener('DOMContentLoaded', async () => {
  // Step 16: load saved locale before first paint so labels render correctly.
  if (typeof I18N !== 'undefined') {
    await I18N.init();
  }
  applyStaticTranslations();

  // ── DOM references ──
  const pageTypeBadge = document.getElementById('pageTypeBadge');
  const pageUrl = document.getElementById('pageUrl');
  const scrapeBtn = document.getElementById('scrapeBtn');
  const actionHint = document.getElementById('actionHint');
  const progressSection = document.getElementById('progressSection');
  const progressCount = document.getElementById('progressCount');
  const progressBar = document.getElementById('progressBar');
  const exportSection = document.getElementById('exportSection');
  const exportBtn = document.getElementById('exportBtn');
  const resetBtn = document.getElementById('resetBtn');
  const apiUploadBtn = document.getElementById('apiUploadBtn');
  const langToggle = document.getElementById('langToggle');
  const loginBtn = document.getElementById('loginBtn');

  // Step 14-1: Degradation UI elements
  const degradeSection = document.getElementById('degradeSection');
  const degradeNotice = document.getElementById('degradeNotice');
  const degradeIcon = document.getElementById('degradeIcon');
  const degradeText = document.getElementById('degradeText');
  const feedbackLink = document.getElementById('feedbackLink');

  // Step 14-2: Anti-crawl UI elements
  const antiCrawlSection = document.getElementById('antiCrawlSection');
  const antiCrawlNotice = document.getElementById('antiCrawlNotice');
  const antiCrawlIcon = document.getElementById('antiCrawlIcon');
  const antiCrawlText = document.getElementById('antiCrawlText');
  const antiCrawlSub = document.getElementById('antiCrawlSub');

  // ── State ──
  // Note: throttleTimer + currentPageInfo are declared at module scope (top of
  // file) so the anti-crawl helpers below can reach them. Do NOT re-declare them
  // here with `let` — that would shadow the module-scope vars and reintroduce the
  // ReferenceError-driven hang.
  let isScraping = false;
  let skipUIRestore = false; // Step 14-2: prevent finally block from undoing anti-crawl UI

  // ── Language toggle (Step 16) ──
  if (langToggle) {
    langToggle.addEventListener('click', async () => {
      if (typeof I18N === 'undefined') return;
      await I18N.toggle();
      // Re-render everything that carries text in the new locale.
      applyStaticTranslations();
      // The page-type badge is always safe to re-render.
      if (currentPageInfo) {
        updatePageTypeUI(currentPageInfo);
      }
      // Fix 2026-07-15: never re-render the action UI while an operation is
      // managing the scrape button. updateActionUI() resets button.disabled and
      // the hint, which would re-enable the button mid-scrape or wipe an active
      // throttle countdown / anti-crawl notice. The countdown + anti-crawl text
      // already re-translate themselves on their own tick (they call t() live).
      const antiCrawlSection = document.getElementById('antiCrawlSection');
      const buttonManaged =
        isScraping ||
        throttleTimer !== null ||
        (antiCrawlSection && !antiCrawlSection.hidden);
      if (currentPageInfo && !buttonManaged) {
        if (currentPageInfo.degradation?.degraded) {
          updateActionUIForDegradation(currentPageInfo);
        } else {
          updateActionUI(currentPageInfo);
        }
      }
      renderLoginState(lastLoginState);
    });
  }

  // ── Login button (Step 16) — open the site login page ──
  if (loginBtn) {
    loginBtn.addEventListener('click', () => {
      chrome.tabs.create({ url: 'https://www.clueai-reviewlens.com/login' });
    });
  }

  // ── Initialization ──
  try {
    // 0. Step 16: check login state (non-blocking for scraping).
    checkLogin().then(renderLoginState);

    // 1. Detect page type
    currentPageInfo = await getPageInfo();
    updatePageTypeUI(currentPageInfo);

    // 2. Check for stored degradation info (Step 14-1)
    if (currentPageInfo.degradation?.degraded) {
      showDegradationUI(currentPageInfo.degradation, currentPageInfo.url);
      updateActionUIForDegradation(currentPageInfo);
    } else {
      updateActionUI(currentPageInfo);
    }

    // 3. Check if reviews already exist for this tab
    const status = await getScrapeStatus();
    if (status.total_reviews > 0) {
      updateProgressUI(status.total_reviews);
      showExportUI(true);
      updateHintForExistingReviews(status.total_reviews);
    }

    // 4. Step 14-2: Check throttle + consecutive zeros on init
    if (status.throttled) {
      showAntiCrawlUI('throttle', { wait_ms: status.throttle_wait_ms });
      startThrottleCountdown(status.throttle_wait_ms);
    } else if (status.consecutive_zeros >= 3) {
      // Show warning but keep button enabled (user can still try)
      actionHint.textContent = t('anticrawl_zeros', { n: status.consecutive_zeros });
      actionHint.className = 'action-hint action-hint--muted';
    }
  } catch (err) {
    console.error('[ReviewLens Popup] Init error:', err);
    pageTypeBadge.textContent = t('badge_detect_failed');
    pageTypeBadge.className = 'badge badge--error';
    pageUrl.textContent = t('detect_failed_hint');
    scrapeBtn.disabled = true;
  }

  // ── Scrape button ──
  scrapeBtn.addEventListener('click', async () => {
    if (isScraping) return;

    isScraping = true;
    setScrapingUI(true);
    hideAntiCrawlUI(); // Step 14-2: clear any previous anti-crawl notice

    try {
      const result = await startScraping();

      // ── Step 14-2: Handle throttled response ──
      if (result.throttled) {
        skipUIRestore = true;
        hideDegradationUI();
        showAntiCrawlUI('throttle', { wait_ms: result.wait_ms });
        startThrottleCountdown(result.wait_ms);
        return;
      }

      // ── Step 14-2: Handle CAPTCHA detection ──
      if (result.captcha_detected) {
        skipUIRestore = true;
        hideDegradationUI();
        showAntiCrawlUI('captcha');
        updateActionUIForDegradation(currentPageInfo);
        return;
      }

      if (result.success) {
        // Step 14-1: Check for degradation first
        if (result.stats?.degraded) {
          const degradation = {
            degraded: true,
            degrade_reason: result.stats.degrade_reason,
            degrade_detail: result.stats.degrade_detail,
            page_type: result.stats.page_type || currentPageInfo?.pageType,
          };
          hideDegradationUI();
          showDegradationUI(degradation, currentPageInfo?.url);
          updateActionUIForDegradation(currentPageInfo);
          return;
        }

        // Normal success path — clear any previous degradation
        hideDegradationUI();
        updateProgressUI(result.total_reviews);
        showExportUI(true);

        if (result.new_reviews > 0) {
          actionHint.textContent = t('scrape_done_new', {
            n: result.new_reviews,
            total: result.total_reviews,
          });
          actionHint.className = 'action-hint action-hint--info';
        } else if (result.total_reviews > 0) {
          actionHint.textContent = t('scrape_no_new', { total: result.total_reviews });
          actionHint.className = 'action-hint';
        } else {
          // Step 14-2: Check consecutive zeros warning
          if (result.consecutive_zeros >= 3) {
            actionHint.textContent = t('anticrawl_zeros', { n: result.consecutive_zeros });
            actionHint.className = 'action-hint action-hint--muted';
          } else {
            // Step 14-1: degraded=false but 0 reviews — gentle reminder
            actionHint.textContent = t('scrape_zero_page');
            actionHint.className = 'action-hint action-hint--muted';
          }
          scrapeBtn.disabled = false;
        }
      } else {
        actionHint.textContent = t('scrape_failed', { msg: result.error || t('err_unknown') });
        actionHint.className = 'action-hint action-hint--muted';
      }
    } catch (err) {
      console.error('[ReviewLens Popup] Scrape error:', err);
      actionHint.textContent = t('scrape_failed', { msg: err.message || t('err_unknown') });
      actionHint.className = 'action-hint action-hint--muted';
    } finally {
      isScraping = false;
      // Step 14-2: skip UI restore when anti-crawl is active (countdown/CAPTCHA manages the button)
      if (!skipUIRestore) {
        setScrapingUI(false);
      }
      skipUIRestore = false;
    }
  });

  // ── Export button ──
  exportBtn.addEventListener('click', async () => {
    exportBtn.disabled = true;
    exportBtn.textContent = t('export_btn_exporting');

    try {
      const result = await exportCsv();
      if (result.success) {
        actionHint.textContent = t('export_done', {
          n: result.total_exported,
          filename: result.filename,
        });
        actionHint.className = 'action-hint action-hint--info';
        exportBtn.textContent = t('export_btn_done');
        setTimeout(() => {
          exportBtn.textContent = t('export_btn');
          exportBtn.disabled = false;
        }, 2000);
      } else {
        actionHint.textContent = t('export_failed', { msg: result.error || t('err_unknown') });
        actionHint.className = 'action-hint action-hint--muted';
        exportBtn.textContent = t('export_btn');
        exportBtn.disabled = false;
      }
    } catch (err) {
      console.error('[ReviewLens Popup] Export error:', err);
      actionHint.textContent = t('export_failed', { msg: err.message || t('err_unknown') });
      actionHint.className = 'action-hint action-hint--muted';
      exportBtn.textContent = t('export_btn');
      exportBtn.disabled = false;
    }
  });

  // ── Reset button ──
  resetBtn.addEventListener('click', async () => {
    resetBtn.disabled = true;
    resetBtn.textContent = t('reset_btn_clearing');

    try {
      await clearReviews();
      updateProgressUI(0);
      showExportUI(false);
      actionHint.textContent = t('reset_done');
      actionHint.className = 'action-hint';
      resetBtn.textContent = t('reset_btn');
      resetBtn.disabled = false;
    } catch (err) {
      console.error('[ReviewLens Popup] Clear error:', err);
      resetBtn.textContent = t('reset_btn');
      resetBtn.disabled = false;
    }
  });

  // ── Upload to API button (Step 15) ──
  if (apiUploadBtn) {
    apiUploadBtn.addEventListener('click', async () => {
    apiUploadBtn.disabled = true;
    apiUploadBtn.textContent = t('upload_btn_uploading');

    try {
      const result = await uploadToApi();
      if (result.success) {
        actionHint.textContent = t('upload_done', {
          n: result.new_reviews,
          dup: result.duplicate_count,
        });
        actionHint.className = 'action-hint action-hint--info';
        // Clear local progress since reviews are now on the server
        updateProgressUI(0);
        showExportUI(false);
        apiUploadBtn.textContent = t('upload_btn_done');
        setTimeout(() => {
          apiUploadBtn.textContent = t('upload_btn');
          apiUploadBtn.disabled = false;
        }, 3000);
      } else if (result.error === 'needs_login') {
        actionHint.textContent = t('login_hint_required');
        actionHint.className = 'action-hint action-hint--muted';
        apiUploadBtn.textContent = t('upload_btn');
        apiUploadBtn.disabled = false;
        // Step 16: refresh the login indicator — session likely expired.
        checkLogin().then(renderLoginState);
      } else {
        // Translate by error code so English users don't see backend Chinese text.
        actionHint.textContent = t('upload_failed', { msg: uploadErrorMessage(result.error) });
        actionHint.className = 'action-hint action-hint--muted';
        apiUploadBtn.textContent = t('upload_btn');
        apiUploadBtn.disabled = false;
      }
    } catch (err) {
      console.error('[ReviewLens Popup] Upload error:', err);
      actionHint.textContent = t('upload_failed', { msg: t('upload_err_network') });
      actionHint.className = 'action-hint action-hint--muted';
      apiUploadBtn.textContent = t('upload_btn');
      apiUploadBtn.disabled = false;
    }
  });
  } // end if (apiUploadBtn)

  // ── UI helpers ──

  function setScrapingUI(active) {
    if (active) {
      scrapeBtn.disabled = true;
      scrapeBtn.textContent = t('scrape_btn_scraping');
    } else {
      scrapeBtn.disabled = false;
      scrapeBtn.textContent = t('scrape_btn_continue');
    }
  }

  function updateProgressUI(total) {
    progressCount.textContent = t('progress_count', { n: total });
    progressSection.hidden = total === 0;

    // Animate progress bar (visual only, up to 100%)
    const maxExpected = 100; // visual cap
    const pct = Math.min(100, Math.round((total / maxExpected) * 100));
    progressBar.style.width = pct + '%';
  }

  function showExportUI(show) {
    exportSection.hidden = !show;
    if (show) {
      exportBtn.disabled = false;
      exportBtn.textContent = t('export_btn');
    }
  }

  function updateHintForExistingReviews(total) {
    scrapeBtn.textContent = t('scrape_btn_continue');
    actionHint.textContent = t('hint_existing', { total });
    actionHint.className = 'action-hint action-hint--info';
  }
});

// ═══════════════════════════════════════════════════════════════
// i18n rendering (Step 16)
// ═══════════════════════════════════════════════════════════════

/**
 * Apply translations to all static [data-i18n] elements plus the
 * language toggle label/title. Safe to call repeatedly (on load + toggle).
 */
function applyStaticTranslations() {
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (key) el.textContent = t(key);
  });
  const langToggle = document.getElementById('langToggle');
  if (langToggle) {
    langToggle.textContent = t('lang_toggle_label');
    langToggle.title = t('lang_toggle_title');
  }
  // Keep the <html lang> attribute in sync for a11y / screen readers.
  const locale = (typeof I18N !== 'undefined') ? I18N.getLocale() : 'zh-CN';
  document.documentElement.lang = locale;
}

/**
 * Render the login indicator from a CHECK_LOGIN result (Step 16).
 * Caches the state so a language toggle can re-render it.
 * @param {object|null} state — { logged_in, username, plan } or null on error
 */
function renderLoginState(state) {
  lastLoginState = state;
  const dot = document.getElementById('loginDot');
  const text = document.getElementById('loginText');
  const btn = document.getElementById('loginBtn');
  if (!dot || !text || !btn) return;

  if (state && state.logged_in) {
    dot.className = 'login-dot login-dot--in';
    let label = t('login_logged_in', { username: state.username || '—' });
    if (state.plan) {
      label += ' · ' + t('login_plan', { plan: state.plan });
    }
    text.textContent = label;
    btn.hidden = true;
  } else if (state && state.success === false && state.error === 'network_error') {
    // Could not reach the API — don't claim "logged out"; keep it neutral.
    dot.className = 'login-dot';
    text.textContent = t('login_checking');
    btn.hidden = true;
  } else {
    dot.className = 'login-dot login-dot--out';
    text.textContent = t('login_logged_out');
    btn.hidden = false;
  }
}

/**
 * Map a backend upload error code to a localized message (Step 16).
 * Falls back to a generic API-error string for unknown codes so no raw
 * backend text (which may be Chinese) leaks into the English UI.
 */
function uploadErrorMessage(code) {
  switch (code) {
    case 'network_error': return t('upload_err_network');
    case 'no_reviews': return t('upload_err_no_reviews');
    case 'api_error':
    default:
      return t('upload_err_api');
  }
}

// ═══════════════════════════════════════════════════════════════
// Background communication
// ═══════════════════════════════════════════════════════════════

/**
 * Query page info for the active tab via service worker
 */
async function getPageInfo() {
  return new Promise((resolve, reject) => {
    try {
      if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
        resolve({ pageType: 'unknown', url: null });
        return;
      }
      chrome.runtime.sendMessage({ type: 'GET_PAGE_INFO' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve(response || { pageType: 'unknown', url: null });
      });
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Check ClueAI login state via the service worker (Step 16).
 * Never rejects — resolves to a state object the UI can render.
 */
async function checkLogin() {
  return new Promise((resolve) => {
    try {
      if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
        resolve({ success: false, logged_in: false, error: 'no_runtime' });
        return;
      }
      chrome.runtime.sendMessage({ type: 'CHECK_LOGIN' }, (response) => {
        if (chrome.runtime.lastError) {
          resolve({ success: false, logged_in: false, error: 'network_error' });
          return;
        }
        resolve(response || { success: false, logged_in: false });
      });
    } catch (_) {
      resolve({ success: false, logged_in: false, error: 'network_error' });
    }
  });
}

/**
 * Get current scrape status (stored reviews) for active tab
 */
async function getScrapeStatus() {
  return new Promise((resolve) => {
    try {
      if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
        console.warn('[ReviewLens Popup] chrome.runtime.sendMessage not available');
        resolve({ total_reviews: 0, reviews: [], page_info: null });
        return;
      }
      chrome.runtime.sendMessage({ type: 'GET_SCRAPE_STATUS' }, (response) => {
        if (chrome.runtime.lastError) {
          console.error('[ReviewLens Popup] getScrapeStatus error:', chrome.runtime.lastError);
          resolve({ total_reviews: 0, reviews: [], page_info: null });
          return;
        }
        resolve(response || { total_reviews: 0, reviews: [], page_info: null });
      });
    } catch (err) {
      console.error('[ReviewLens Popup] getScrapeStatus exception:', err);
      resolve({ total_reviews: 0, reviews: [], page_info: null });
    }
  });
}

/**
 * Trigger review scraping on the active tab.
 *
 * Fix 2026-07-15: guard against a dead service worker. Manifest V3 kills the
 * background worker after ~30s of inactivity; if it dies mid-request the
 * sendMessage callback never fires and this Promise would hang forever,
 * leaving the popup stuck on "抓取中…". A 30s timeout rejects instead so the
 * click handler's catch/finally resets the UI. (Background caps its own work
 * at ~20s via EXTRACT_REVIEWS timeout, so 30s leaves comfortable margin.)
 */
async function startScraping() {
  return new Promise((resolve, reject) => {
    try {
      if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
        reject(new Error('chrome.runtime.sendMessage not available'));
        return;
      }

      let settled = false;
      const timer = setTimeout(() => {
        if (settled) return;
        settled = true;
        reject(new Error(t('scrape_timeout')));
      }, 30000);

      chrome.runtime.sendMessage({ type: 'START_SCRAPING' }, (response) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve(response || { success: false, error: 'no_response' });
      });
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Export accumulated reviews as CSV file
 */
async function exportCsv() {
  return new Promise((resolve, reject) => {
    try {
      if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
        reject(new Error('chrome.runtime.sendMessage not available'));
        return;
      }
      chrome.runtime.sendMessage({ type: 'EXPORT_CSV' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve(response || { success: false, error: 'no_response' });
      });
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Clear accumulated reviews for active tab
 */
async function clearReviews() {
  return new Promise((resolve, reject) => {
    try {
      if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
        reject(new Error('chrome.runtime.sendMessage not available'));
        return;
      }
      chrome.runtime.sendMessage({ type: 'CLEAR_REVIEWS' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve(response || { success: false });
      });
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Upload accumulated reviews to ClueAI API (Step 15)
 */
async function uploadToApi() {
  return new Promise((resolve, reject) => {
    try {
      if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
        reject(new Error('chrome.runtime.sendMessage not available'));
        return;
      }
      chrome.runtime.sendMessage({ type: 'UPLOAD_TO_API' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        resolve(response || { success: false, error: 'no_response' });
      });
    } catch (err) {
      reject(err);
    }
  });
}

// ═══════════════════════════════════════════════════════════════
// UI update functions
// ═══════════════════════════════════════════════════════════════

/**
 * Update the page type badge and URL display
 */
function updatePageTypeUI(pageInfo) {
  const badge = document.getElementById('pageTypeBadge');
  const urlEl = document.getElementById('pageUrl');

  // Display URL (truncated)
  if (pageInfo.url) {
    try {
      const u = new URL(pageInfo.url);
      urlEl.textContent = u.hostname + u.pathname;
      urlEl.title = pageInfo.url; // full URL on hover
    } catch {
      urlEl.textContent = pageInfo.url || '';
    }
  } else {
    urlEl.textContent = t('page_not_amazon');
  }

  // Set badge
  switch (pageInfo.pageType) {
    case 'product':
      badge.textContent = t('badge_product');
      badge.className = 'badge badge--product';
      break;
    case 'reviews':
      badge.textContent = t('badge_reviews');
      badge.className = 'badge badge--reviews';
      break;
    case 'amazon_other':
      badge.textContent = t('badge_amazon_other');
      badge.className = 'badge badge--other';
      break;
    case 'not_amazon':
      badge.textContent = t('badge_not_amazon');
      badge.className = 'badge badge--not-amazon';
      break;
    case 'unknown':
    default:
      badge.textContent = t('badge_unknown');
      badge.className = 'badge badge--unknown';
      break;
  }
}

/**
 * Update the action button and hint based on page type
 */
function updateActionUI(pageInfo) {
  const scrapeBtn = document.getElementById('scrapeBtn');
  const actionHint = document.getElementById('actionHint');

  if (pageInfo.pageType === 'product' || pageInfo.pageType === 'reviews') {
    scrapeBtn.disabled = false;
    scrapeBtn.textContent = t('scrape_btn');
    actionHint.textContent = t('hint_click_to_scrape');
    actionHint.className = 'action-hint';
  } else if (pageInfo.pageType === 'not_amazon') {
    scrapeBtn.disabled = true;
    scrapeBtn.textContent = t('scrape_btn');
    actionHint.textContent = t('hint_goto_amazon');
    actionHint.className = 'action-hint action-hint--muted';
  } else if (pageInfo.pageType === 'amazon_other') {
    scrapeBtn.disabled = true;
    scrapeBtn.textContent = t('scrape_btn');
    actionHint.textContent = t('hint_goto_product');
    actionHint.className = 'action-hint action-hint--muted';
  } else {
    scrapeBtn.disabled = true;
    actionHint.textContent = '';
  }
}

// ═══════════════════════════════════════════════════════════════
// Degradation UI (Step 14-1)
// ═══════════════════════════════════════════════════════════════

/**
 * Display degradation notice based on extraction stats.
 * @param {object} degradation — { degraded, degrade_reason, degrade_detail, page_type }
 * @param {string} [tabUrl] — the actual tab URL (not popup URL)
 */
function showDegradationUI(degradation, tabUrl) {
  const degradeSection = document.getElementById('degradeSection');
  const degradeNotice = document.getElementById('degradeNotice');
  const degradeIcon = document.getElementById('degradeIcon');
  const degradeText = document.getElementById('degradeText');
  const feedbackLink = document.getElementById('feedbackLink');
  const scrapeBtn = document.getElementById('scrapeBtn');
  const actionHint = document.getElementById('actionHint');

  degradeSection.hidden = false;
  scrapeBtn.disabled = true;
  actionHint.textContent = '';

  const pageType = degradation.page_type || 'reviews';

  if (pageType === 'reviews') {
    // Reviews page — structure may have changed, show warning + feedback link
    degradeNotice.className = 'degrade-notice degrade-notice--warning';
    degradeIcon.textContent = '⚠️';
    degradeText.textContent = t('degrade_reviews');
    feedbackLink.hidden = false;
    // Build feedback link with the actual tab URL
    try {
      var fbUrl = tabUrl || '';
      feedbackLink.href =
        'https://www.clueai-reviewlens.com/feedback?reason=' +
        encodeURIComponent(degradation.degrade_reason || '') +
        '&url=' + encodeURIComponent(fbUrl);
    } catch (_) {
      feedbackLink.href = 'https://www.clueai-reviewlens.com/feedback';
    }
  } else if (pageType === 'product') {
    // Product page — no review list, guide user to reviews page
    degradeNotice.className = 'degrade-notice degrade-notice--info';
    degradeIcon.textContent = 'ℹ️';
    degradeText.textContent = t('degrade_product');
    feedbackLink.hidden = true;
  } else {
    // Other pages (amazon_other, not_amazon, etc.)
    degradeNotice.className = 'degrade-notice degrade-notice--info';
    degradeIcon.textContent = 'ℹ️';
    degradeText.textContent = t('degrade_other');
    feedbackLink.hidden = true;
  }

  // Append technical detail for diagnostics
  if (degradation.degrade_detail) {
    // Remove any previously appended detail
    var oldDetail = degradeText.querySelector('.degrade-detail');
    if (oldDetail) oldDetail.remove();
    var detailEl = document.createElement('p');
    detailEl.className = 'degrade-detail';
    detailEl.textContent = degradation.degrade_detail;
    degradeText.appendChild(detailEl);
  }
}

/**
 * Hide the degradation notice.
 */
function hideDegradationUI() {
  const degradeSection = document.getElementById('degradeSection');
  const feedbackLink = document.getElementById('feedbackLink');
  const degradeText = document.getElementById('degradeText');

  if (degradeSection) degradeSection.hidden = true;
  if (feedbackLink) feedbackLink.hidden = true;
  // Clear any previously appended detail paragraph
  if (degradeText) {
    const detailEl = degradeText.querySelector('.degrade-detail');
    if (detailEl) detailEl.remove();
  }
}

/**
 * Update the action button for degraded state (Step 14-1).
 * Grey out the scrape button and show the appropriate hint.
 */
function updateActionUIForDegradation(pageInfo) {
  const scrapeBtn = document.getElementById('scrapeBtn');
  const actionHint = document.getElementById('actionHint');

  scrapeBtn.disabled = true;
  scrapeBtn.textContent = t('scrape_btn');

  const pageType = pageInfo.pageType || 'reviews';

  if (pageType === 'reviews') {
    actionHint.textContent = '';
  } else if (pageType === 'product') {
    actionHint.textContent = '';
  } else {
    actionHint.textContent = t('hint_goto_reviews');
    actionHint.className = 'action-hint action-hint--muted';
  }
}

// ═══════════════════════════════════════════════════════════════
// Anti-Crawl UI (Step 14-2)
// ═══════════════════════════════════════════════════════════════

/**
 * Display anti-crawl notice.
 * @param {'captcha'|'throttle'|'zeros'} type — warning type
 * @param {object} [extra] — extra data (wait_ms for throttle, count for zeros)
 */
function showAntiCrawlUI(type, extra) {
  hideDegradationUI(); // CAPTCHA/throttle takes priority over degradation

  const antiCrawlSection = document.getElementById('antiCrawlSection');
  const antiCrawlNotice = document.getElementById('antiCrawlNotice');
  const antiCrawlIcon = document.getElementById('antiCrawlIcon');
  const antiCrawlText = document.getElementById('antiCrawlText');
  const antiCrawlSub = document.getElementById('antiCrawlSub');

  antiCrawlSection.hidden = false;
  antiCrawlSub.hidden = true;

  switch (type) {
    case 'captcha':
      antiCrawlNotice.className = 'anticrawl-notice anticrawl-notice--captcha';
      antiCrawlIcon.textContent = '🛑';
      antiCrawlText.textContent = t('anticrawl_captcha');
      break;

    case 'throttle': {
      const waitSec = Math.ceil((extra?.wait_ms || 3000) / 1000);
      antiCrawlNotice.className = 'anticrawl-notice anticrawl-notice--throttle';
      antiCrawlIcon.textContent = '⏳';
      antiCrawlText.textContent = t('anticrawl_throttle', { n: waitSec });
      break;
    }

    case 'zeros':
      antiCrawlNotice.className = 'anticrawl-notice anticrawl-notice--zeros';
      antiCrawlIcon.textContent = '⚠️';
      antiCrawlText.textContent = t('anticrawl_zeros', { n: extra?.count || 3 });
      break;
  }
}

/**
 * Hide the anti-crawl notice and clear any running countdown.
 */
function hideAntiCrawlUI() {
  const antiCrawlSection = document.getElementById('antiCrawlSection');
  if (antiCrawlSection) antiCrawlSection.hidden = true;
  if (throttleTimer) {
    clearInterval(throttleTimer);
    throttleTimer = null;
  }
}

/**
 * Start a countdown timer on the scrape button.
 * Button stays disabled until countdown reaches 0.
 * @param {number} waitMs — milliseconds to wait
 */
function startThrottleCountdown(waitMs) {
  // Clear any existing timer
  if (throttleTimer) {
    clearInterval(throttleTimer);
    throttleTimer = null;
  }

  const scrapeBtn = document.getElementById('scrapeBtn');
  const antiCrawlText = document.getElementById('antiCrawlText');
  scrapeBtn.disabled = true;

  let remaining = Math.ceil(waitMs / 1000);

  const updateCountdown = () => {
    if (remaining <= 0) {
      clearInterval(throttleTimer);
      throttleTimer = null;
      scrapeBtn.disabled = false;
      scrapeBtn.textContent = t('scrape_btn');
      hideAntiCrawlUI();
      // Restore normal hint text
      const actionHint = document.getElementById('actionHint');
      if (actionHint && currentPageInfo &&
          (currentPageInfo.pageType === 'product' || currentPageInfo.pageType === 'reviews')) {
        actionHint.textContent = t('hint_click_to_scrape');
        actionHint.className = 'action-hint';
      }
      return;
    }

    scrapeBtn.textContent = t('scrape_btn_wait', { n: remaining });
    if (antiCrawlText) {
      antiCrawlText.textContent = t('anticrawl_throttle', { n: remaining });
    }
    remaining--;
  };

  updateCountdown(); // immediate first update
  throttleTimer = setInterval(updateCountdown, 1000);
}
