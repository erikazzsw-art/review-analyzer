/**
 * ClueAI ReviewLens — Content Script
 *
 * Injected into Amazon product/review pages.
 * Step 10: detect page type and report to service worker.
 * Step 11: multi-selector fallback + review DOM extraction.
 * Step 12: MutationObserver pagination + postMessage bridge to background.
 * Step 13: two-way postMessage bridge for accumulated reviews from inject.js.
 */

(function () {
  'use strict';

  // @@VERSION: 2026-07-22-v5 — Strategy D: colorToAsin parsing (ImageBlockBTF)
  console.log('[ReviewLens CS] content.js loaded — version 2026-07-22-v5');

  // ═══════════════════════════════════════════════════════════════
  // Page Type Detection (Step 10)
  // ═══════════════════════════════════════════════════════════════

  /**
   * Detect the current Amazon page type based on URL
   * @returns {'product' | 'reviews' | 'amazon_other' | 'not_amazon'}
   */
  function detectPageType() {
    const url = window.location.href;
    const isLocalTest = /localhost|127\.0\.0\.1/.test(url);

    if (!/amazon\./.test(url) && !isLocalTest) {
      return 'not_amazon';
    }

    // Product detail page: /dp/<10-char ASIN>
    if (/\/dp\/[A-Z0-9]{10}/i.test(url)) {
      return 'product';
    }

    // Review page: /product-reviews/<ASIN>
    if (/\/product-reviews\//i.test(url)) {
      return 'reviews';
    }

    return 'amazon_other';
  }

  const pageType = detectPageType();

  // Report to service worker on script injection
  if (typeof chrome !== 'undefined' && chrome.runtime?.sendMessage) {
    try {
      chrome.runtime.sendMessage({
        type: 'PAGE_TYPE_DETECTED',
        pageType,
        url: window.location.href,
      }).catch(() => {
        // Service worker may not be ready yet; that's fine
      });
    } catch {
      // chrome.runtime may not be available
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // Marketplace Mapping
  // ═══════════════════════════════════════════════════════════════

  const MARKETPLACE_MAP = {
    'amazon.com': 'US',
    'amazon.co.uk': 'UK',
    'amazon.de': 'DE',
    'amazon.fr': 'FR',
    'amazon.es': 'ES',
    'amazon.it': 'IT',
    'amazon.co.jp': 'JP',
    'amazon.ca': 'CA',
    'amazon.in': 'IN',
    'amazon.com.au': 'AU',
    'amazon.com.br': 'BR',
    'amazon.com.mx': 'MX',
    'amazon.nl': 'NL',
    'amazon.se': 'SE',
    'amazon.pl': 'PL',
    'amazon.sg': 'SG',
    'amazon.ae': 'AE',
    'amazon.sa': 'SA',
    'amazon.tr': 'TR',
  };

  function getMarketplace() {
    const hostname = window.location.hostname;
    // Strip leading "www." and match
    const clean = hostname.replace(/^www\./, '');
    return MARKETPLACE_MAP[clean] || clean.toUpperCase();
  }

  // ═══════════════════════════════════════════════════════════════
  // Selector Sets (priority order: first with >0 matches wins)
  // ═══════════════════════════════════════════════════════════════

  const SELECTOR_SETS = [
    // Set 1: data-hook attributes (most common, most stable)
    {
      name: 'data-hook-v1',
      container: '[data-hook="review"]',
      rating: '[data-hook="review-star-rating"] .a-icon-alt',
      title: '[data-hook="review-title"]',
      body: '[data-hook="review-body"]',
      date: '[data-hook="review-date"]',
      author: '.a-profile-name',
      verified: '[data-hook="avp-badge"]',
      helpful: '[data-hook="helpful-vote-statement"]',
    },
    // Set 2: alternative data-hook nesting
    {
      name: 'data-hook-v2',
      container: 'div[data-hook="review"]',
      rating: 'i[data-hook="review-star-rating"] span',
      title: 'a[data-hook="review-title"] span:last-child',
      body: 'span[data-hook="review-body"] span',
      date: 'span[data-hook="review-date"]',
      author: 'span.a-profile-name',
      verified: 'span[data-hook="avp-badge"]',
      helpful: 'span[data-hook="helpful-vote-statement"]',
    },
    // Set 3: generic class fallback (last resort)
    {
      name: 'class-fallback',
      container: '.review',
      rating: '.review-rating .a-icon-alt, i.a-icon-star .a-icon-alt',
      title: '.review-title',
      body: '.review-text, .review-body',
      date: '.review-date',
      author: '.author',
      verified: '.avp-badge',
      helpful: '.helpful-votes',
    },
  ];

  // ═══════════════════════════════════════════════════════════════
  // Utility Helpers
  // ═══════════════════════════════════════════════════════════════

  /**
   * Safely get trimmed text from an element + selector combo.
   * Returns '' if element or selector doesn't match.
   */
  function getText(parent, selector) {
    if (!parent || !selector) return '';
    try {
      const el = parent.querySelector(selector);
      return el ? (el.textContent || '').trim() : '';
    } catch {
      return '';
    }
  }

  /**
   * Check if an element matching the selector exists.
   */
  function hasElement(parent, selector) {
    if (!parent || !selector) return false;
    try {
      return !!parent.querySelector(selector);
    } catch {
      return false;
    }
  }

  /**
   * Generate a random review ID
   */
  function randomId() {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let id = 'rev_';
    for (let i = 0; i < 16; i++) {
      id += chars[Math.floor(Math.random() * chars.length)];
    }
    return id;
  }

  // ═══════════════════════════════════════════════════════════════
  // Field Parsers
  // ═══════════════════════════════════════════════════════════════

  /**
   * Parse rating from text like "5.0 out of 5 stars" → 5.0
   * Handles locale variants: "4,0 von 5 Sternen", aria-label, etc.
   */
  function parseRating(text) {
    if (!text) return null;
    // Try "X.X out of" pattern (English)
    let match = text.match(/(\d+[.,]?\d*)\s*out\s*of/i);
    if (match) {
      return parseFloat(match[1].replace(',', '.'));
    }
    // Try "X.X von" pattern (German)
    match = text.match(/(\d+[.,]?\d*)\s*von/i);
    if (match) {
      return parseFloat(match[1].replace(',', '.'));
    }
    // Try plain number at the start
    match = text.match(/^(\d+[.,]?\d*)/);
    if (match) {
      return parseFloat(match[1].replace(',', '.'));
    }
    return null;
  }

  /**
   * Parse helpful count from text like "123 people found this helpful" → 123
   * Handles "One person found this helpful" → 1
   */
  function parseHelpfulCount(text) {
    if (!text) return 0;
    // "One person" special case
    if (/\bone\b/i.test(text)) return 1;
    // Extract first integer
    const match = text.match(/(\d[\d,]*)/);
    if (match) {
      return parseInt(match[1].replace(/,/g, ''), 10);
    }
    return 0;
  }

  /**
   * Try to parse an Amazon date string to ISO 8601.
   * Common formats:
   *   "Reviewed in the United States on January 15, 2025"
   *   "Revisado en España el 15 de enero de 2025"
   *   "Reviewed in Germany on 15. Januar 2025"
   * Returns null if parsing fails.
   */
  function parseDateToISO(text) {
    if (!text) return null;
    try {
      // Try native Date parsing first (handles "January 15, 2025")
      const d = new Date(text);
      if (!isNaN(d.getTime())) {
        return d.toISOString();
      }
      // Try extracting "Month DD, YYYY" from within text
      const monthMatch = text.match(
        /(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}/i
      );
      if (monthMatch) {
        const d2 = new Date(monthMatch[0]);
        if (!isNaN(d2.getTime())) {
          return d2.toISOString();
        }
      }
    } catch {
      // fall through
    }
    return null;
  }

  /**
   * Try to extract a review ID from the container element.
   * Checks common attributes and permalink patterns.
   */
  function getReviewId(container, index) {
    if (!container) return randomId();

    // Try id attribute directly
    const elId = container.getAttribute('id');
    if (elId && /^[A-Za-z0-9_-]{10,}$/.test(elId)) {
      return elId;
    }

    // Try data-review-id
    const dataId = container.getAttribute('data-review-id');
    if (dataId) return dataId;

    // Try to extract from permalink href (e.g. "...review/R1234567890/...")
    try {
      const permalink = container.querySelector('a[href*="review/"], a[href*="/review/"]');
      if (permalink) {
        const href = permalink.getAttribute('href') || '';
        const reviewMatch = href.match(/\/review\/([A-Za-z0-9]+)/);
        if (reviewMatch) return reviewMatch[1];
      }
    } catch {
      // fall through
    }

    // Try data-customer-id + timestamp as composite
    const cid = container.getAttribute('data-customer-id');
    if (cid) return `cust_${cid}_${index}`;

    return randomId();
  }

  // ═══════════════════════════════════════════════════════════════
  // Core: Extract a single review from a container element
  // ═══════════════════════════════════════════════════════════════

  /**
   * Extract one review's fields from a container DOM element
   * using the given selector set.
   */
  function extractOneReview(container, selectors, index) {
    const ratingText =
      getText(container, selectors.rating) ||
      container.getAttribute('aria-label') || '';
    const dateText = getText(container, selectors.date);

    return {
      review_id: getReviewId(container, index),
      body: getText(container, selectors.body),
      rating: parseRating(ratingText),
      date: dateText,
      date_iso: parseDateToISO(dateText),
      reviewer: getText(container, selectors.author),
      title: getText(container, selectors.title),
      verified: hasElement(container, selectors.verified),
      helpful_count: parseHelpfulCount(getText(container, selectors.helpful)),
      marketplace: getMarketplace(),
      scraped_at: new Date().toISOString(),
      page_url: window.location.href,
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // CAPTCHA Detection (Step 14-2)
  // ═══════════════════════════════════════════════════════════════

  /**
   * Detect Amazon CAPTCHA / Robot Check page.
   * Checks multiple DOM indicators; returns true if ≥ 2 match.
   * @returns {boolean}
   */
  function detectCaptcha() {
    try {
      var indicators = [
        document.title.includes('Robot Check'),
        document.title.includes('CAPTCHA'),
        !!document.querySelector('form[action*="validateCaptcha"]'),
        !!document.querySelector('#captchacharacters'),
        !!document.querySelector('img[src*="captcha"]'),
        document.body.innerText.includes('Type the characters you see'),
        document.body.innerText.includes('Enter the characters'),
      ];
      return indicators.filter(Boolean).length >= 2;
    } catch (_) {
      return false;
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // Core: extractReviews() — main entry point
  // ═══════════════════════════════════════════════════════════════

  /**
   * Degradation reason enum values (Step 14-1).
   * @enum {string}
   */
  const DEGRADE_REASON = {
    NO_SELECTOR_MATCH: 'no_selector_match',
    EMPTY_CONTAINERS: 'empty_containers',
    SELECTOR_PARSE_ERROR: 'selector_parse_error',
    TIMEOUT: 'timeout',
  };

  /**
   * Human-readable degradation details keyed by reason (Step 14-1).
   */
  const DEGRADE_DETAIL_MAP = {
    no_selector_match:
      '已尝试 3 组选择器（data-hook-v1 / data-hook-v2 / class-fallback），均未匹配到评论容器。页面 DOM 结构可能已更新。',
    empty_containers: '',
    selector_parse_error:
      '选择器语法异常，可能被 CSP 拦截或页面环境限制。',
    timeout:
      '单页提取超时（> 30 秒），页面可能包含异常数量的评论或脚本阻塞。',
  };

  /** Max extraction time before timeout degradation (Step 14-1) */
  var MAX_EXTRACTION_TIME_MS = 30000;

  /**
   * Extract all reviews from the current page.
   *
   * Tries each selector set in priority order. The first set
   * that produces >0 container matches is used for extraction.
   *
   * When all selectors fail, degradation info is attached to stats
   * so the popup can show an appropriate message (Step 14-1).
   *
   * @returns {{ reviews: Array<object>, stats: object }}
   */
  function extractReviews() {
    const startTime = performance.now();

    // ── Step 14-2: CAPTCHA check before anything else ──
    if (detectCaptcha()) {
      return {
        reviews: [],
        stats: {
          total_found: 0,
          total_extracted: 0,
          selector_set_used: null,
          extraction_time_ms: Math.round(performance.now() - startTime),
          marketplace: getMarketplace(),
          page_type: detectPageType(),
          captcha_detected: true,
          degraded: true,
          degrade_reason: 'captcha',
          degrade_detail:
            'Amazon CAPTCHA / Robot Check 页面检测到验证码，无法自动抓取。请手动完成验证码后刷新页面重试。',
        },
      };
    }

    let selectedSet = null;
    let containers = [];
    const selectorErrors = [];

    for (const selectorSet of SELECTOR_SETS) {
      try {
        const nodes = document.querySelectorAll(selectorSet.container);
        if (nodes.length > 0) {
          selectedSet = selectorSet;
          containers = Array.from(nodes);
          break;
        }
      } catch (err) {
        selectorErrors.push({ setName: selectorSet.name, error: String(err) });
        continue;
      }
    }

    // ── No selector set matched → degradation ──
    if (!selectedSet || containers.length === 0) {
      const elapsed = Math.round(performance.now() - startTime);
      var degradeReason, degradeDetail;

      if (selectorErrors.length === SELECTOR_SETS.length) {
        // All selector sets threw parse errors (e.g. CSP blocked)
        degradeReason = DEGRADE_REASON.SELECTOR_PARSE_ERROR;
        degradeDetail = DEGRADE_DETAIL_MAP.selector_parse_error;
      } else {
        // Selectors ran but matched nothing
        degradeReason = DEGRADE_REASON.NO_SELECTOR_MATCH;
        degradeDetail = DEGRADE_DETAIL_MAP.no_selector_match;
      }

      return {
        reviews: [],
        stats: {
          total_found: 0,
          total_extracted: 0,
          selector_set_used: null,
          extraction_time_ms: elapsed,
          marketplace: getMarketplace(),
          page_type: detectPageType(),
          degraded: true,
          degrade_reason: degradeReason,
          degrade_detail: degradeDetail,
        },
      };
    }

    // ── Extract reviews from matched containers ──
    const reviews = [];
    let failed = 0;
    let emptyCount = 0;

    for (let i = 0; i < containers.length; i++) {
      try {
        const review = extractOneReview(containers[i], selectedSet, i);
        reviews.push(review);
        // Track containers that yielded no meaningful content
        if (!review.body && review.rating == null && !review.title) {
          emptyCount++;
        }
      } catch (err) {
        failed++;
        emptyCount++;
        console.warn('[ReviewLens CS] Failed to extract review at index', i, err);
      }
    }

    const elapsed = Math.round(performance.now() - startTime);

    // ── Timeout check (Step 14-1) ──
    if (elapsed > MAX_EXTRACTION_TIME_MS) {
      return {
        reviews: [],
        stats: {
          total_found: containers.length,
          total_extracted: 0,
          total_failed: failed,
          selector_set_used: selectedSet.name,
          extraction_time_ms: elapsed,
          marketplace: getMarketplace(),
          page_type: detectPageType(),
          degraded: true,
          degrade_reason: DEGRADE_REASON.TIMEOUT,
          degrade_detail: DEGRADE_DETAIL_MAP.timeout,
        },
      };
    }

    // ── Empty containers check (Step 14-1): all containers produced empty reviews ──
    if (reviews.length > 0 && emptyCount === containers.length) {
      return {
        reviews: [],
        stats: {
          total_found: containers.length,
          total_extracted: 0,
          total_failed: failed,
          selector_set_used: selectedSet.name,
          extraction_time_ms: elapsed,
          marketplace: getMarketplace(),
          page_type: detectPageType(),
          degraded: true,
          degrade_reason: DEGRADE_REASON.EMPTY_CONTAINERS,
          degrade_detail:
            '选择器匹配到 ' + containers.length + ' 个评论容器，但所有容器内评论字段（正文/评分/标题）均为空。页面结构可能已变更。',
        },
      };
    }

    return {
      reviews,
      stats: {
        total_found: containers.length,
        total_extracted: reviews.length,
        total_failed: failed,
        selector_set_used: selectedSet.name,
        extraction_time_ms: elapsed,
        marketplace: getMarketplace(),
        page_type: detectPageType(),
        degraded: false,
      },
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // Message Handling
  // ═══════════════════════════════════════════════════════════════

  if (typeof chrome !== 'undefined' && chrome.runtime?.onMessage) {
    chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    // ── Step 10: page detection ──
    if (message.type === 'DETECT_PAGE') {
      sendResponse({
        pageType: detectPageType(),
        url: window.location.href,
        title: document.title,
      });
      return true;
    }

    // ── Step 11: review extraction ──
    if (message.type === 'EXTRACT_REVIEWS') {
      const result = extractReviews();
      sendResponse(result);
      return true;
    }

    // ── Step 14-2: standalone CAPTCHA detection ──
    if (message.type === 'DETECT_CAPTCHA') {
      sendResponse({ captcha_detected: detectCaptcha() });
      return true;
    }

    // ── Step 13: get accumulated reviews from inject.js ──
    if (message.type === 'GET_ACCUMULATED_REVIEWS') {
      requestAccumulatedReviews()
        .then((reviews) => {
          sendResponse({ success: true, reviews });
        })
        .catch((err) => {
          sendResponse({ success: false, error: String(err) });
        });
      return true; // keep channel open for async
    }

    // ── Step 11.5: extract product listing from inject.js ──
    if (message.type === 'EXTRACT_LISTING') {
      requestListing()
        .then((listing) => {
          sendResponse({ success: true, listing: listing.listing, variations: listing.variations });
        })
        .catch((err) => {
          sendResponse({ success: false, error: String(err) });
        });
      return true; // keep channel open for async
    }
  });
  }

  // ═══════════════════════════════════════════════════════════════
  // PostMessage bridge: inject.js (MAIN world) ↔ content.js (ISOLATED)
  //
  // Step 12: inject.js notifies content.js of new pagination reviews.
  // Step 13: content.js can query inject.js for accumulated reviews.
  // ═══════════════════════════════════════════════════════════════

  // Pending requests for inject.js queries (keyed by requestId)
  var pendingRequests = {};

  window.addEventListener('message', function (event) {
    // Only accept messages from the same window
    if (event.source !== window) return;

    var data = event.data;
    if (!data) return;

    // ── Step 12: pagination notification from inject.js ──
    if (data.type === 'REVIEWLENS_NEW_REVIEWS') {
      console.log(
        '[ReviewLens CS] 收到分页通知:',
        data.count, '条新评论，累计', data.total, '条'
      );

      // Forward to background service worker
      if (chrome.runtime?.sendMessage) {
        chrome.runtime.sendMessage({
          type: 'EXTRACT_REVIEWS_RESULT',
          count: data.count,
          total: data.total,
          url: window.location.href,
          timestamp: Date.now(),
        }).catch(function () {
          // Service worker may not be ready; that's fine
        });
      }
    }

    // ── Step 13: response from inject.js with accumulated reviews ──
    if (data.type === 'REVIEWLENS_REVIEWS_RESPONSE') {
      var requestId = data.requestId;
      if (requestId && pendingRequests[requestId]) {
        clearTimeout(pendingRequests[requestId].timer);
        pendingRequests[requestId].resolve(data.reviews || []);
        delete pendingRequests[requestId];
      }
    }

    // ── Step 11.5: listing/variations response from inject.js ──
    if (data.type === 'REVIEWLENS_LISTING_RESPONSE' || data.type === 'REVIEWLENS_VARIATIONS_RESPONSE') {
      var requestId = data.requestId;
      if (requestId && pendingRequests[requestId]) {
        // Collect listing + variations responses; resolve when both arrive
        var entry = pendingRequests[requestId];
        if (data.type === 'REVIEWLENS_LISTING_RESPONSE') {
          entry.listing = data.listing || null;
        } else {
          entry.variations = data.variations || null;
        }
        // Resolve when both have arrived (or after timeout in requestListing)
        if (entry.listing !== undefined && entry.variations !== undefined) {
          clearTimeout(entry.timer);
          entry.resolve({ listing: entry.listing, variations: entry.variations });
          delete pendingRequests[requestId];
        }
      }
    }
  });

  /**
   * Request accumulated reviews from inject.js (MAIN world).
   * Uses postMessage with a unique requestId for response matching.
   * Returns a Promise that resolves with the reviews array.
   */
  function requestAccumulatedReviews() {
    return new Promise(function (resolve, reject) {
      var requestId = 'req_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);

      // Set a timeout to avoid hanging indefinitely
      var timer = setTimeout(function () {
        delete pendingRequests[requestId];
        resolve([]); // resolve empty rather than reject — inject.js may not be loaded
      }, 2000);

      pendingRequests[requestId] = { resolve: resolve, reject: reject, timer: timer };

      window.postMessage(
        { type: 'REVIEWLENS_GET_REVIEWS', requestId: requestId },
        '*'
      );
    });
  }

  /**
   * Request product listing + variations from inject.js (MAIN world).
   * Sends two parallel postMessage requests and waits for both responses.
   * Returns a Promise that resolves with { listing, variations }.
   * Step 11.5: Product listing scrape.
   */
  function requestListing() {
    return new Promise(function (resolve, reject) {
      var requestId = 'lst_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);

      var timer = setTimeout(function () {
        // Resolve with whatever we got so far
        var entry = pendingRequests[requestId];
        if (entry) {
          entry.resolve({
            listing: entry.listing || null,
            variations: entry.variations || null,
          });
          delete pendingRequests[requestId];
        }
      }, 3000);

      pendingRequests[requestId] = {
        resolve: resolve,
        reject: reject,
        timer: timer,
        listing: undefined,
        variations: undefined,
      };

      // Request both listing and variations in parallel
      window.postMessage(
        { type: 'REVIEWLENS_GET_LISTING', requestId: requestId },
        '*'
      );
      window.postMessage(
        { type: 'REVIEWLENS_GET_VARIATIONS', requestId: requestId },
        '*'
      );
    });
  }

  // ═══════════════════════════════════════════════════════════════
  // Bridge: inject extraction logic into MAIN world via <script src>
  //
  // Manifest V3 content scripts run in ISOLATED world by default.
  // DevTools Console runs in MAIN world — window.__REVIEWLENS__ set
  // directly here is invisible.
  //
  // Solution: inject a <script src="inject.js"> tag. The browser
  // loads the extension-packaged file and executes it in the MAIN
  // world. Configuration is passed via data attributes on the
  // script element.
  //
  // We use script.src (NOT script.textContent) because inline scripts
  // are blocked by the page's Content Security Policy.
  // ═══════════════════════════════════════════════════════════════

  function injectMainWorld() {
    // Dedup: check if inject.js was already injected
    if (window.__REVIEWLENS__) {
      console.log('[ReviewLens CS] injectMainWorld: already injected, skipped');
      return;
    }
    try {
      if (typeof chrome === 'undefined' || !chrome.runtime?.getURL) {
        console.error('[ReviewLens CS] injectMainWorld: chrome.runtime.getURL not available');
        return;
      }
      const script = document.createElement('script');
      script.src = chrome.runtime.getURL('inject.js');
      script.setAttribute('data-marketplace-map', JSON.stringify(MARKETPLACE_MAP));
      script.setAttribute('data-selector-sets', JSON.stringify(SELECTOR_SETS));
      script.onload = function () {
        console.log('[ReviewLens CS] injectMainWorld: inject.js loaded successfully');
      };
      script.onerror = function () {
        console.error('[ReviewLens CS] injectMainWorld: inject.js failed to load');
      };
      const target = document.head || document.documentElement;
      if (!target) {
        console.error('[ReviewLens CS] No head or documentElement to append script');
        return;
      }
      target.appendChild(script);
      // Note: do NOT remove the script element — external scripts
      // load asynchronously and need the element to remain in DOM.
    } catch (e) {
      console.error('[ReviewLens CS] injectMainWorld failed:', e);
    }
  }

  // Run injection immediately
  injectMainWorld();

  console.log('[ReviewLens CS] Content script loaded —', pageType);
  console.log('[ReviewLens CS] DevTools: run window.__REVIEWLENS__.extractReviews() to test');
})();
