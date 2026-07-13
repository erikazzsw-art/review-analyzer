/**
 * ClueAI ReviewLens — Content Script
 *
 * Injected into Amazon product/review pages.
 * Step 10: detect page type and report to service worker.
 * Step 11: multi-selector fallback + review DOM extraction.
 * Future steps: pagination handling, CSV export, popup trigger.
 */

(function () {
  'use strict';

  // ═══════════════════════════════════════════════════════════════
  // Page Type Detection (Step 10)
  // ═══════════════════════════════════════════════════════════════

  /**
   * Detect the current Amazon page type based on URL
   * @returns {'product' | 'reviews' | 'amazon_other' | 'not_amazon'}
   */
  function detectPageType() {
    const url = window.location.href;

    if (!/amazon\./.test(url)) {
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
  chrome.runtime
    .sendMessage({
      type: 'PAGE_TYPE_DETECTED',
      pageType,
      url: window.location.href,
    })
    .catch(() => {
      // Service worker may not be ready yet; that's fine
    });

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
  // Core: extractReviews() — main entry point
  // ═══════════════════════════════════════════════════════════════

  /**
   * Extract all reviews from the current page.
   *
   * Tries each selector set in priority order. The first set
   * that produces >0 container matches is used for extraction.
   *
   * @returns {{ reviews: Array<object>, stats: object }}
   */
  function extractReviews() {
    const startTime = performance.now();

    let selectedSet = null;
    let containers = [];

    for (const selectorSet of SELECTOR_SETS) {
      try {
        const nodes = document.querySelectorAll(selectorSet.container);
        if (nodes.length > 0) {
          selectedSet = selectorSet;
          containers = Array.from(nodes);
          break;
        }
      } catch {
        // Invalid selector, skip to next set
        continue;
      }
    }

    // No selector set matched — return empty
    if (!selectedSet || containers.length === 0) {
      const elapsed = Math.round(performance.now() - startTime);
      return {
        reviews: [],
        stats: {
          total_found: 0,
          total_extracted: 0,
          selector_set_used: null,
          extraction_time_ms: elapsed,
          marketplace: getMarketplace(),
          page_type: detectPageType(),
        },
      };
    }

    const reviews = [];
    let failed = 0;

    for (let i = 0; i < containers.length; i++) {
      try {
        const review = extractOneReview(containers[i], selectedSet, i);
        reviews.push(review);
      } catch (err) {
        failed++;
        console.warn('[ReviewLens CS] Failed to extract review at index', i, err);
      }
    }

    const elapsed = Math.round(performance.now() - startTime);

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
      },
    };
  }

  // ═══════════════════════════════════════════════════════════════
  // Message Handling
  // ═══════════════════════════════════════════════════════════════

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
  });

  // ═══════════════════════════════════════════════════════════════
  // Bridge: inject extraction logic into MAIN world via <script> tag
  //
  // Manifest V3 content scripts run in ISOLATED world by default.
  // DevTools Console runs in MAIN world — window.__REVIEWLENS__ set
  // directly here is invisible.
  //
  // Solution: inject a <script> tag with a self-contained copy of
  // the extraction logic. <script> tags created by content scripts
  // execute in the page's MAIN world, making window.__REVIEWLENS__
  // directly accessible from DevTools Console (no async bridge needed).
  // ═══════════════════════════════════════════════════════════════

  function injectMainWorld() {
    const script = document.createElement('script');
    script.textContent = `
(function() {
  var MARKETPLACE_MAP = ${JSON.stringify(MARKETPLACE_MAP)};

  function getMarketplace() {
    var clean = window.location.hostname.replace(/^www\\./, '');
    return MARKETPLACE_MAP[clean] || clean.toUpperCase();
  }

  var SELECTOR_SETS = ${JSON.stringify(SELECTOR_SETS)};

  function detectPageType() {
    var url = window.location.href;
    if (!/amazon\\./.test(url)) return 'not_amazon';
    if (/\\/dp\\/[A-Z0-9]{10}/i.test(url)) return 'product';
    if (/\\/product-reviews\\//i.test(url)) return 'reviews';
    return 'amazon_other';
  }

  function getText(parent, selector) {
    if (!parent || !selector) return '';
    try { var el = parent.querySelector(selector); return el ? (el.textContent || '').trim() : ''; } catch(e) { return ''; }
  }

  function hasElement(parent, selector) {
    if (!parent || !selector) return false;
    try { return !!parent.querySelector(selector); } catch(e) { return false; }
  }

  function randomId() {
    var chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    var id = 'rev_';
    for (var i = 0; i < 16; i++) id += chars[Math.floor(Math.random() * chars.length)];
    return id;
  }

  function parseRating(text) {
    if (!text) return null;
    var match = text.match(/(\\d+[.,]?\\d*)\\s*out\\s*of/i);
    if (match) return parseFloat(match[1].replace(',', '.'));
    match = text.match(/(\\d+[.,]?\\d*)\\s*von/i);
    if (match) return parseFloat(match[1].replace(',', '.'));
    match = text.match(/^(\\d+[.,]?\\d*)/);
    if (match) return parseFloat(match[1].replace(',', '.'));
    return null;
  }

  function parseHelpfulCount(text) {
    if (!text) return 0;
    if (/\\bone\\b/i.test(text)) return 1;
    var match = text.match(/(\\d[\\d,]*)/);
    if (match) return parseInt(match[1].replace(/,/g, ''), 10);
    return 0;
  }

  function parseDateToISO(text) {
    if (!text) return null;
    try {
      var d = new Date(text);
      if (!isNaN(d.getTime())) return d.toISOString();
      var monthMatch = text.match(/(January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2},?\\s+\\d{4}/i);
      if (monthMatch) { var d2 = new Date(monthMatch[0]); if (!isNaN(d2.getTime())) return d2.toISOString(); }
    } catch(e) {}
    return null;
  }

  function getReviewId(container, index) {
    if (!container) return randomId();
    var elId = container.getAttribute('id');
    if (elId && /^[A-Za-z0-9_-]{10,}\$/.test(elId)) return elId;
    var dataId = container.getAttribute('data-review-id');
    if (dataId) return dataId;
    try {
      var permalink = container.querySelector('a[href*="review/"], a[href*="/review/"]');
      if (permalink) { var href = permalink.getAttribute('href') || ''; var m = href.match(/\\/review\\/([A-Za-z0-9]+)/); if (m) return m[1]; }
    } catch(e) {}
    var cid = container.getAttribute('data-customer-id');
    if (cid) return 'cust_' + cid + '_' + index;
    return randomId();
  }

  function extractReviews() {
    var startTime = performance.now();
    var selectedSet = null;
    var containers = [];

    for (var s = 0; s < SELECTOR_SETS.length; s++) {
      try {
        var nodes = document.querySelectorAll(SELECTOR_SETS[s].container);
        if (nodes.length > 0) { selectedSet = SELECTOR_SETS[s]; containers = Array.from(nodes); break; }
      } catch(e) { continue; }
    }

    if (!selectedSet || containers.length === 0) {
      return { reviews: [], stats: { total_found: 0, total_extracted: 0, selector_set_used: null, extraction_time_ms: Math.round(performance.now() - startTime), marketplace: getMarketplace(), page_type: detectPageType() } };
    }

    var reviews = [];
    var failed = 0;
    for (var i = 0; i < containers.length; i++) {
      try {
        var c = containers[i];
        var ratingText = getText(c, selectedSet.rating) || c.getAttribute('aria-label') || '';
        var dateText = getText(c, selectedSet.date);
        reviews.push({
          review_id: getReviewId(c, i),
          body: getText(c, selectedSet.body),
          rating: parseRating(ratingText),
          date: dateText,
          date_iso: parseDateToISO(dateText),
          reviewer: getText(c, selectedSet.author),
          title: getText(c, selectedSet.title),
          verified: hasElement(c, selectedSet.verified),
          helpful_count: parseHelpfulCount(getText(c, selectedSet.helpful)),
          marketplace: getMarketplace(),
          scraped_at: new Date().toISOString(),
          page_url: window.location.href
        });
      } catch(e) { failed++; }
    }

    return {
      reviews: reviews,
      stats: {
        total_found: containers.length,
        total_extracted: reviews.length,
        total_failed: failed,
        selector_set_used: selectedSet.name,
        extraction_time_ms: Math.round(performance.now() - startTime),
        marketplace: getMarketplace(),
        page_type: detectPageType()
      }
    };
  }

  window.__REVIEWLENS__ = {
    extractReviews: extractReviews,
    detectPageType: detectPageType,
    getMarketplace: getMarketplace
  };
})();
`;
    (document.head || document.documentElement).appendChild(script);
    script.remove();
  }

  injectMainWorld();

  console.log('[ReviewLens CS] Content script loaded —', pageType);
  console.log('[ReviewLens CS] DevTools: run window.__REVIEWLENS__.extractReviews() to test');
})();
