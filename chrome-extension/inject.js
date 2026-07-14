/**
 * ClueAI ReviewLens — MAIN World Injection Script
 *
 * This file is loaded via <script src="..."> created by content.js.
 * It runs in the page's MAIN world, making window.__REVIEWLENS__
 * directly accessible from DevTools Console.
 *
 * Configuration (MARKETPLACE_MAP, SELECTOR_SETS) is passed via
 * data attributes on the script element.
 */

(function () {
  'use strict';

  try {
    // ── Read configuration from the script tag's data attributes ──
    var scriptTag = document.currentScript;
    if (!scriptTag) {
      console.error('[ReviewLens MAIN] Cannot find currentScript');
      return;
    }

    var MARKETPLACE_MAP = JSON.parse(scriptTag.getAttribute('data-marketplace-map') || '{}');
    var SELECTOR_SETS = JSON.parse(scriptTag.getAttribute('data-selector-sets') || '[]');

    // ═══════════════════════════════════════════════════════════════
    // Marketplace
    // ═══════════════════════════════════════════════════════════════

    function getMarketplace() {
      var clean = window.location.hostname.replace(/^www\./, '');
      return MARKETPLACE_MAP[clean] || clean.toUpperCase();
    }

    // ═══════════════════════════════════════════════════════════════
    // Page Type Detection
    // ═══════════════════════════════════════════════════════════════

    function detectPageType() {
      var url = window.location.href;
      if (!/amazon\./.test(url)) return 'not_amazon';
      if (/\/dp\/[A-Z0-9]{10}/i.test(url)) return 'product';
      if (/\/product-reviews\//i.test(url)) return 'reviews';
      return 'amazon_other';
    }

    // ═══════════════════════════════════════════════════════════════
    // Utility Helpers
    // ═══════════════════════════════════════════════════════════════

    function getText(parent, selector) {
      if (!parent || !selector) return '';
      try {
        var el = parent.querySelector(selector);
        return el ? (el.textContent || '').trim() : '';
      } catch (e) {
        return '';
      }
    }

    function hasElement(parent, selector) {
      if (!parent || !selector) return false;
      try {
        return !!parent.querySelector(selector);
      } catch (e) {
        return false;
      }
    }

    function randomId() {
      var chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
      var id = 'rev_';
      for (var i = 0; i < 16; i++) {
        id += chars[Math.floor(Math.random() * chars.length)];
      }
      return id;
    }

    // ═══════════════════════════════════════════════════════════════
    // Field Parsers
    // ═══════════════════════════════════════════════════════════════

    function parseRating(text) {
      if (!text) return null;
      var match = text.match(/(\d+[.,]?\d*)\s*out\s*of/i);
      if (match) return parseFloat(match[1].replace(',', '.'));
      match = text.match(/(\d+[.,]?\d*)\s*von/i);
      if (match) return parseFloat(match[1].replace(',', '.'));
      match = text.match(/^(\d+[.,]?\d*)/);
      if (match) return parseFloat(match[1].replace(',', '.'));
      return null;
    }

    function parseHelpfulCount(text) {
      if (!text) return 0;
      if (/\bone\b/i.test(text)) return 1;
      var match = text.match(/(\d[\d,]*)/);
      if (match) return parseInt(match[1].replace(/,/g, ''), 10);
      return 0;
    }

    function parseDateToISO(text) {
      if (!text) return null;
      try {
        var d = new Date(text);
        if (!isNaN(d.getTime())) return d.toISOString();
        var monthMatch = text.match(
          /(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}/i
        );
        if (monthMatch) {
          var d2 = new Date(monthMatch[0]);
          if (!isNaN(d2.getTime())) return d2.toISOString();
        }
      } catch (e) {}
      return null;
    }

    function getReviewId(container, index) {
      if (!container) return randomId();

      var elId = container.getAttribute('id');
      if (elId && /^[A-Za-z0-9_-]{10,}$/.test(elId)) return elId;

      var dataId = container.getAttribute('data-review-id');
      if (dataId) return dataId;

      try {
        var permalink = container.querySelector('a[href*="review/"], a[href*="/review/"]');
        if (permalink) {
          var href = permalink.getAttribute('href') || '';
          var m = href.match(/\/review\/([A-Za-z0-9]+)/);
          if (m) return m[1];
        }
      } catch (e) {}

      var cid = container.getAttribute('data-customer-id');
      if (cid) return 'cust_' + cid + '_' + index;

      return randomId();
    }

    // ═══════════════════════════════════════════════════════════════
    // Core: extractReviews()
    // ═══════════════════════════════════════════════════════════════

    function extractReviews() {
      var startTime = performance.now();

      var selectedSet = null;
      var containers = [];

      for (var s = 0; s < SELECTOR_SETS.length; s++) {
        try {
          var nodes = document.querySelectorAll(SELECTOR_SETS[s].container);
          if (nodes.length > 0) {
            selectedSet = SELECTOR_SETS[s];
            containers = Array.from(nodes);
            break;
          }
        } catch (e) {
          continue;
        }
      }

      if (!selectedSet || containers.length === 0) {
        var elapsed = Math.round(performance.now() - startTime);
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

      var reviews = [];
      var failed = 0;

      for (var i = 0; i < containers.length; i++) {
        try {
          var c = containers[i];
          var ratingText =
            getText(c, selectedSet.rating) ||
            c.getAttribute('aria-label') ||
            '';
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
            helpful_count: parseHelpfulCount(
              getText(c, selectedSet.helpful)
            ),
            marketplace: getMarketplace(),
            scraped_at: new Date().toISOString(),
            page_url: window.location.href,
          });
        } catch (e) {
          failed++;
        }
      }

      var elapsed = Math.round(performance.now() - startTime);

      return {
        reviews: reviews,
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
    // Expose on window for DevTools access
    // ═══════════════════════════════════════════════════════════════

    window.__REVIEWLENS__ = {
      extractReviews: extractReviews,
      detectPageType: detectPageType,
      getMarketplace: getMarketplace,
    };

    console.log('[ReviewLens MAIN] window.__REVIEWLENS__ ready ✓');
  } catch (e) {
    console.error('[ReviewLens MAIN] Injection error:', e);
  }
})();
