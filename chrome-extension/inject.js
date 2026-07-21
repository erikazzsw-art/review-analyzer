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
    // Dedup: if already injected (e.g. content script re-ran), skip
    if (window.__REVIEWLENS__) {
      return;
    }

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
      var isLocalTest = /localhost|127\.0\.0\.1/.test(url);
      if (!/amazon\./.test(url) && !isLocalTest) return 'not_amazon';
      if (/\/dp\/[A-Z0-9]{10}/i.test(url)) return 'product';
      if (/\/product-reviews\//i.test(url)) return 'reviews';
      return isLocalTest ? 'amazon_other' : 'amazon_other';
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
    // Step 11.5: Product Listing Extraction
    // ═══════════════════════════════════════════════════════════════

    /**
     * Extract a value from DOM using primary + fallback selectors.
     * Returns the first non-empty match, or '' if none.
     */
    function extractField(selectors) {
      for (var i = 0; i < selectors.length; i++) {
        try {
          var el = document.querySelector(selectors[i]);
          if (el) {
            var text = (el.textContent || '').trim();
            if (text) return text;
          }
        } catch (e) {
          continue;
        }
      }
      return '';
    }

    /**
     * Extract all bullet point texts from the page.
     */
    function extractBulletPoints() {
      var selectors = ['#feature-bullets li', '#featurebullets_feature_div li', '.a-unordered-list.a-vertical li'];
      for (var s = 0; s < selectors.length; s++) {
        try {
          var nodes = document.querySelectorAll(selectors[s]);
          if (nodes.length > 0) {
            var points = [];
            for (var i = 0; i < nodes.length; i++) {
              var text = (nodes[i].textContent || '').trim();
              if (text && text.length > 2) {
                points.push(text);
              }
            }
            if (points.length > 0) return points;
          }
        } catch (e) {
          continue;
        }
      }
      return [];
    }

    /**
     * Extract current price from the page.
     * Handles deal prices, sale prices, and regular prices.
     */
    function extractPrice() {
      // Try the primary price first (.a-price .a-offscreen, excluding text-price)
      try {
        var priceEls = document.querySelectorAll('.a-price .a-offscreen');
        for (var i = 0; i < priceEls.length; i++) {
          var parent = priceEls[i].closest('.a-price');
          if (parent && parent.classList.contains('a-text-price')) continue;
          var text = (priceEls[i].textContent || '').trim();
          if (text) return text;
        }
      } catch (e) {}

      var fallbacks = ['#priceblock_ourprice', '#priceblock_dealprice', '#price_inside_buybox',
                        '.a-price span[aria-hidden="true"]', '[data-a-size="xl"] .a-price .a-offscreen'];
      return extractField(fallbacks);
    }

    /**
     * Extract original/list price (strikethrough).
     */
    function extractOriginalPrice() {
      var selectors = [
        '.a-price.a-text-price .a-offscreen',
        '#listPrice',
        '.basisPrice .a-offscreen',
        'span.priceBlockStrikePriceString',
      ];
      return extractField(selectors);
    }

    /**
     * Parse price text like "$19.99" or "¥1,980" to {amount, currency}.
     */
    function parsePriceText(text) {
      if (!text) return { amount: null, currency: 'USD' };
      var cleaned = text.replace(/[\s ]/g, '').trim();
      var match = cleaned.match(/^([^\d]*)([\d,]+\.?\d*)/);
      if (!match) return { amount: null, currency: 'USD' };
      var symbol = match[1];
      var numStr = match[2].replace(/,/g, '');
      var amount = parseFloat(numStr);
      if (isNaN(amount)) return { amount: null, currency: 'USD' };
      var currencyMap = { '$': 'USD', '£': 'GBP', '€': 'EUR', '¥': 'JPY' };
      var currency = currencyMap[symbol] || symbol || 'USD';
      return { amount: amount, currency: currency };
    }

    /**
     * Extract main product listing information from the current page.
     */
    function extractProductListing() {
      var startTime = performance.now();
      var priceText = extractPrice();
      var origPriceText = extractOriginalPrice();
      var priceParsed = parsePriceText(priceText);
      var origParsed = parsePriceText(origPriceText);

      var bulletPoints = extractBulletPoints();
      var ratingText = extractField(['#acrPopover .a-icon-alt', '[data-hook="rating-out-of-text"]',
                                      '.a-icon-star .a-icon-alt', '#averageCustomerReviews .a-icon-alt']);
      var rating = null;
      if (ratingText) {
        var ratingMatch = ratingText.match(/(\d+[.,]?\d*)/);
        if (ratingMatch) rating = parseFloat(ratingMatch[1].replace(',', '.'));
      }

      var ratingsTotalText = extractField(['#acrCustomerReviewText', '[data-hook="total-review-count"]']);
      var ratingsTotal = null;
      if (ratingsTotalText) {
        var rtMatch = ratingsTotalText.match(/([\d,]+)/);
        if (rtMatch) ratingsTotal = parseInt(rtMatch[1].replace(/,/g, ''), 10);
      }

      // Extract ASIN from URL or hidden input
      var asin = '';
      try {
        var urlMatch = window.location.href.match(/\/dp\/([A-Z0-9]{10})/i);
        if (urlMatch) asin = urlMatch[1];
        if (!asin) {
          var asinInput = document.querySelector('input[name="ASIN"], input[id="ASIN"]');
          if (asinInput) asin = asinInput.value || '';
        }
      } catch (e) {}

      var brandText = extractField(['#bylineInfo', '[data-csa-c="brand-name"]', '#brand']);
      var brand = brandText.replace(/^(Brand:|品牌:|Visit the\s*|访问\s*|Store|商店)/gi, '').trim();
      if (/^about this item$/i.test(brand)) brand = '';

      var description = extractField(['#productDescription', '[data-csa-c="product-description"]',
                                       '#aplus_feature_div .aplus-v2']);

      var mainImageUrl = '';
      var imgSelectors = ['#imgTagWrapperId img', '#landingImage', '#imgBlkFront', '.imgTagWrapper img'];
      for (var is = 0; is < imgSelectors.length; is++) {
        try {
          var imgEl = document.querySelector(imgSelectors[is]);
          if (imgEl) {
            var src = imgEl.getAttribute('src') || imgEl.src || '';
            if (src && /^(https?:)?\/\//.test(src)) {
              mainImageUrl = src;
              break;
            }
          }
        } catch (e) {
          continue;
        }
      }

      var sellerName = extractField(['#merchant-info', '#sellerProfileTriggerId', '[data-csa-c-seller-name]']);
      var availability = extractField(['#availability', '#availability span', '.a-size-medium.a-color-success']);
      var dimensions = extractField(['#productDetails_techSpec_section_1', '.prodDetSectionEntry']);

      // Parse BSR
      var bestSellerRank = [];
      var bsrText = extractField(['#SalesRank', '#detailBulletsWrapper_feature_div']);
      if (bsrText) {
        var bsrRegex = /#(\d[\d,]*)\s*(?:in|en)\s+([^(\n]+?)(?:\s*\(|$)/gi;
        var bsrMatch;
        while ((bsrMatch = bsrRegex.exec(bsrText)) !== null) {
          bestSellerRank.push({
            category: bsrMatch[2].trim(),
            rank: parseInt(bsrMatch[1].replace(/,/g, ''), 10),
          });
        }
      }

      var elapsed = Math.round(performance.now() - startTime);

      return {
        asin: asin,
        marketplace: getMarketplace(),
        url: window.location.href,
        title: extractField(['#productTitle', '[data-csa-c="product-title"]', '#title']),
        price: priceParsed.amount,
        price_currency: priceParsed.currency,
        price_text: priceText,
        original_price: origParsed.amount,
        original_price_text: origPriceText,
        rating: rating,
        ratings_total: ratingsTotal,
        brand: brand,
        bullet_points: bulletPoints,
        main_image_url: mainImageUrl,
        description: description,
        seller_name: sellerName,
        availability: availability,
        dimensions: dimensions,
        best_seller_rank: bestSellerRank,
        extraction_time_ms: elapsed,
      };
    }

    /**
     * Extract variation ASINs and their attributes from the product page.
     *
     * Strategy A (preferred): Parse from internal JSON in <script> tags.
     * Strategy B (fallback): Parse from DOM swatch/twister components.
     */
    function extractVariationAsins() {
      var parentAsin = '';
      try {
        var urlMatch = window.location.href.match(/\/dp\/([A-Z0-9]{10})/i);
        if (urlMatch) parentAsin = urlMatch[1];
      } catch (e) {}

      if (!parentAsin) {
        return { parent_asin: '', variants: [], variation_dimensions: [] };
      }

      // ── Strategy A: Parse from script tag JSON ──
      try {
        var scripts = document.querySelectorAll('script[type="text/javascript"]');
        for (var i = 0; i < scripts.length; i++) {
          var text = scripts[i].textContent || '';

          // Try dimensionValuesDisplayData
          var jsonMatch = text.match(/"dimensionValuesDisplayData"\s*:\s*(\[[\s\S]*?\])\s*[\n;,}]/);
          if (!jsonMatch) {
            jsonMatch = text.match(/"dimensionValuesDisplayData"\s*:\s*(\[[^\]]*\])/);
          }
          if (jsonMatch) {
            try {
              var dimData = JSON.parse(jsonMatch[1]);
              // Extract dimension names from the same script tag
              var dimNames = _extractDimensionNames(text);
              var variants = _parseDimensionDisplayData(dimData, dimNames);
              if (variants && variants.length > 0) {
                return {
                  parent_asin: parentAsin,
                  variants: variants,
                  variation_dimensions: _getVariationDimensions(variants),
                };
              }
            } catch (e) {}
          }

          // Try asinVariationValues
          var altMatch = text.match(/"asinVariationValues"\s*:\s*(\{[^}]+\})/);
          if (!altMatch) {
            altMatch = text.match(/"asinVariants"\s*:\s*(\[[^\]]*\])/);
          }
          if (altMatch) {
            try {
              var altData = JSON.parse(altMatch[1]);
              var altVariants = _parseAsinVariants(altData);
              if (altVariants && altVariants.length > 0) {
                return {
                  parent_asin: parentAsin,
                  variants: altVariants,
                  variation_dimensions: _getVariationDimensions(altVariants),
                };
              }
            } catch (e) {}
          }
        }
      } catch (e) {}

      // ── Strategy B: DOM swatch parsing ──
      var dimSelectors = [
        { selector: '#variation_color_name li[data-defaultasin], #color_name li[data-defaultasin]', name: 'color' },
        { selector: '#variation_size_name li[data-defaultasin], #size_name li[data-defaultasin]', name: 'size' },
        { selector: '#variation_style_name li[data-defaultasin], #style_name li[data-defaultasin]', name: 'style' },
        { selector: '#variation_material_name li[data-defaultasin]', name: 'material' },
      ];

      var dimMaps = [];
      for (var d = 0; d < dimSelectors.length; d++) {
        try {
          var nodes = document.querySelectorAll(dimSelectors[d].selector);
          if (nodes.length > 0) {
            var items = [];
            for (var n = 0; n < nodes.length; n++) {
              var dasin = nodes[n].getAttribute('data-defaultasin') || nodes[n].getAttribute('data-dp-url');
              if (dasin) {
                var asinClean = dasin;
                var asinMatch = dasin.match(/\/dp\/([A-Z0-9]{10})/i);
                if (asinMatch) asinClean = asinMatch[1];
                var label = (nodes[n].textContent || '').trim();
                items.push({ asin: asinClean, value: label || '' });
              }
            }
            if (items.length > 0) {
              dimMaps.push({ name: dimSelectors[d].name, values: items });
            }
          }
        } catch (e) {
          continue;
        }
      }

      if (dimMaps.length > 0) {
        // For multi-dimension: try to build an ASIN map from script data
        var asinMap = null;
        if (dimMaps.length >= 2) {
          asinMap = _buildAsinMapFromScripts();
        }
        var cartVariants = _cartesianProduct(dimMaps, asinMap);
        return {
          parent_asin: parentAsin,
          variants: cartVariants,
          variation_dimensions: dimMaps.map(function(dm) { return dm.name; }),
        };
      }

      // ── Strategy C: twister swatchSelect elements ──
      try {
        var twisterEls = document.querySelectorAll('#twister .swatchSelect[data-defaultasin]');
        if (twisterEls.length > 0) {
          var twisterVariants = [];
          for (var t = 0; t < twisterEls.length; t++) {
            var tasin = twisterEls[t].getAttribute('data-defaultasin') || '';
            var tlabel = (twisterEls[t].textContent || '').trim();
            if (tasin && /^[A-Z0-9]{10}$/i.test(tasin)) {
              twisterVariants.push({ asin: tasin, label: tlabel || '' });
            }
          }
          if (twisterVariants.length > 0) {
            return {
              parent_asin: parentAsin,
              variants: twisterVariants,
              variation_dimensions: [],
            };
          }
        }
      } catch (e) {}

      return { parent_asin: parentAsin, variants: [], variation_dimensions: [] };
    }

    /**
     * Parse dimensionValuesDisplayData structure into variant list.
     */
    function _parseDimensionDisplayData(data, dimensionNames) {
      var variants = [];
      if (!Array.isArray(data)) return variants;
      for (var i = 0; i < data.length; i++) {
        var item = data[i];
        var asin = item.asin || '';
        if (!asin || !/^[A-Z0-9]{10}$/i.test(asin)) continue;
        var variant = { asin: asin };
        if (Array.isArray(item.dimensionValues)) {
          for (var j = 0; j < item.dimensionValues.length; j++) {
            // Map numeric index to actual dimension name (color/size/style/material)
            var dimName = (dimensionNames && dimensionNames[j]) ? dimensionNames[j] : ('dim_' + j);
            variant[dimName] = item.dimensionValues[j];
          }
        }
        if (item.color) variant.color = item.color;
        if (item.size) variant.size = item.size;
        if (item.style) variant.style = item.style;
        if (item.material) variant.material = item.material;
        variants.push(variant);
      }
      return variants;
    }

    /**
     * Parse asinVariationValues into variant list.
     */
    function _parseAsinVariants(data) {
      if (Array.isArray(data)) {
        return data.map(function(v) {
          return typeof v === 'object' ? v : { asin: v || '' };
        }).filter(function(v) { return v.asin && /^[A-Z0-9]{10}$/i.test(v.asin); });
      }
      if (typeof data === 'object') {
        var result = [];
        Object.keys(data).forEach(function(key) {
          result.push({ asin: key, value: data[key] });
        });
        return result;
      }
      return [];
    }

    /**
     * Deduce variation dimension names from variant attributes.
     */
    function _getVariationDimensions(variants) {
      if (!variants || variants.length === 0) return [];
      var dims = [];
      var sample = variants[0];
      if (sample.color !== undefined) dims.push('color');
      if (sample.size !== undefined) dims.push('size');
      if (sample.style !== undefined) dims.push('style');
      if (sample.material !== undefined) dims.push('material');
      for (var key in sample) {
        if (/^dim_\d+$/.test(key)) dims.push(key);
      }
      return dims;
    }

    /**
     * Extract dimension names from a script tag text.
     * Looks for "dimensions":["Color","Size"] or "dimensionLabels":["Color","Size"]
     * Returns an array of lowercase names, or null if not found.
     */
    function _extractDimensionNames(text) {
      try {
        // Try "dimensions":["Color","Size"]
        var m = text.match(/"dimensions"\s*:\s*\[([^\]]*)\]/);
        if (!m) {
          // Try "dimensionLabels":["Color","Size"]
          m = text.match(/"dimensionLabels"\s*:\s*\[([^\]]*)\]/);
        }
        if (!m) {
          // Try "dimensionDisplayLabels":["Color","Size"]
          m = text.match(/"dimensionDisplayLabels"\s*:\s*\[([^\]]*)\]/);
        }
        if (m) {
          var names = JSON.parse('[' + m[1] + ']');
          return names.map(function(n) { return String(n).toLowerCase().replace(/[^a-z]/gi, ''); });
        }
      } catch(e) {}
      return null;
    }

    /**
     * Build an ASIN→dimension mapping from script tags.
     * Searches for dimensionValuesDisplayData entries and builds a map
     * keyed by dimension value combination (e.g. "Black|Large" → "B0XXX").
     */
    function _buildAsinMapFromScripts() {
      try {
        var scripts = document.querySelectorAll('script[type="text/javascript"]');
        for (var i = 0; i < scripts.length; i++) {
          var text = scripts[i].textContent || '';
          var pattern = /"asin"\s*:\s*"([A-Z0-9]{10})"\s*,\s*"dimensionValues"\s*:\s*\[([^\]]*)\]/g;
          var map = {};
          var match;
          while ((match = pattern.exec(text)) !== null) {
            var asin = match[1];
            var rawValues = match[2];
            var dimValues = rawValues.split(',').map(function(s) {
              return s.replace(/["'\s]/g, '');
            }).filter(function(s) { return s.length > 0; });
            if (dimValues.length > 0) {
              map[dimValues.join('|')] = asin;
            }
          }
          if (Object.keys(map).length > 0) return map;
        }
      } catch(e) {}
      return null;
    }

    /**
     * Generate Cartesian product from dimension maps.
     */
    function _cartesianProduct(dimMaps, asinMap) {
      if (dimMaps.length === 0) return [];

      var product = [{}];
      for (var d = 0; d < dimMaps.length; d++) {
        var dim = dimMaps[d];
        var next = [];
        for (var p = 0; p < product.length; p++) {
          for (var v = 0; v < dim.values.length; v++) {
            var entry = {};
            for (var key in product[p]) {
              entry[key] = product[p][key];
            }
            entry[dim.name] = dim.values[v].value;
            if (dimMaps.length === 1) {
              entry.asin = dim.values[v].asin;
            }
            next.push(entry);
          }
        }
        product = next;
      }

      // Multi-dimension: try to assign ASINs for each combination
      if (dimMaps.length > 1) {
        for (var pi = 0; pi < product.length; pi++) {
          var entry = product[pi];
          if (entry.asin) continue;

          // 1. Try asinMap lookup (key: "value1|value2|...")
          if (asinMap) {
            var keys = [];
            for (var di = 0; di < dimMaps.length; di++) {
              keys.push(entry[dimMaps[di].name] || '');
            }
            var mapKey = keys.join('|');
            if (asinMap[mapKey] && /^[A-Z0-9]{10}$/i.test(asinMap[mapKey])) {
              entry.asin = asinMap[mapKey];
              continue;
            }
            // Also try reversed key order
            var revKey = keys.reverse().join('|');
            if (asinMap[revKey] && /^[A-Z0-9]{10}$/i.test(asinMap[revKey])) {
              entry.asin = asinMap[revKey];
              continue;
            }
          }

          // 2. Try DOM li element data attributes
          entry.asin = _findAsinByCombination(dimMaps, entry);
        }
      }

      return product;
    }

    /**
     * Try to find an ASIN by matching dimension combination against
     * DOM swatch li elements' data attributes.
     */
    function _findAsinByCombination(dimMaps, entry) {
      try {
        // Iterate each dimension and look for the matching swatch li
        for (var di = 0; di < dimMaps.length; di++) {
          var dim = dimMaps[di];
          var targetValue = entry[dim.name];
          if (!targetValue) continue;
          var selectors = [
            '#variation_' + dim.name + '_name li',
            '#' + dim.name + '_name li'
          ];
          for (var si = 0; si < selectors.length; si++) {
            try {
              var lis = document.querySelectorAll(selectors[si]);
              for (var li = 0; li < lis.length; li++) {
                var title = (lis[li].getAttribute('title') || '').trim();
                var alt = (lis[li].getAttribute('aria-label') || '').trim();
                var imgAlt = '';
                try {
                  var img = lis[li].querySelector('img');
                  if (img) imgAlt = (img.getAttribute('alt') || '').trim();
                } catch(e) {}
                if (title === targetValue || alt === targetValue || imgAlt === targetValue) {
                  var dasin = lis[li].getAttribute('data-defaultasin') ||
                              lis[li].getAttribute('data-csa-c-item-id') ||
                              lis[li].getAttribute('data-asin') ||
                              '';
                  if (dasin && /^[A-Z0-9]{10}$/i.test(dasin)) {
                    return dasin;
                  }
                }
              }
            } catch(e) {}
          }
        }
      } catch(e) {}
      return '';
    }

    // ═══════════════════════════════════════════════════════════════
    // Expose on window for DevTools access
    // ═══════════════════════════════════════════════════════════════

    window.__REVIEWLENS__ = {
      extractReviews: extractReviews,
      extractProductListing: extractProductListing,
      extractVariationAsins: extractVariationAsins,
      detectPageType: detectPageType,
      getMarketplace: getMarketplace,
      allReviews: [],
      seenIds: new Set(),
    };

    var api = window.__REVIEWLENS__;

    // ═══════════════════════════════════════════════════════════════
    // Pagination: MutationObserver for AJAX page turns (Step 12)
    // ═══════════════════════════════════════════════════════════════

    var debounceTimer = null;

    /**
     * Handle new DOM content detected by MutationObserver.
     * Extracts all reviews currently on the page, deduplicates
     * against seenIds, and accumulates into allReviews.
     */
    function handleNewDOM() {
      var result = extractReviews();
      var newReviews = [];

      for (var i = 0; i < result.reviews.length; i++) {
        var review = result.reviews[i];
        if (!api.seenIds.has(review.review_id)) {
          api.seenIds.add(review.review_id);
          newReviews.push(review);
        }
      }

      if (newReviews.length > 0) {
        api.allReviews = api.allReviews.concat(newReviews);
        console.log(
          '[ReviewLens MAIN] 新评论 ' + newReviews.length + ' 条，累计 ' + api.allReviews.length + ' 条'
        );

        window.postMessage(
          {
            type: 'REVIEWLENS_NEW_REVIEWS',
            count: newReviews.length,
            total: api.allReviews.length,
          },
          '*'
        );
      }
    }

    /**
     * Start MutationObserver on the review list container.
     * On Amazon, the review list is inside #cm_cr-review_list.
     * childList + subtree captures AJAX page turns.
     */
    function startObserver() {
      var target = document.querySelector('#cm_cr-review_list');
      if (!target) {
        console.warn('[ReviewLens MAIN] MutationObserver: 找不到 #cm_cr-review_list，跳过分页监听');
        return;
      }

      var observer = new MutationObserver(function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(handleNewDOM, 500);
      });

      observer.observe(target, { childList: true, subtree: true });
      console.log('[ReviewLens MAIN] MutationObserver 已启动，监听分页变化');
    }

    // ═══════════════════════════════════════════════════════════════
    // Listen for review requests from content script (Step 13)
    //
    // content.js (ISOLATED world) sends postMessage to request the
    // accumulated reviews. We respond with the full allReviews array.
    // ═══════════════════════════════════════════════════════════════

    window.addEventListener('message', function (event) {
      // Only accept messages from the same window
      if (event.source !== window) return;

      var data = event.data;
      if (!data) return;

      // ── Step 13: accumulated reviews request ──
      if (data.type === 'REVIEWLENS_GET_REVIEWS') {
        window.postMessage(
          {
            type: 'REVIEWLENS_REVIEWS_RESPONSE',
            requestId: data.requestId,
            reviews: api.allReviews,
            total: api.allReviews.length,
          },
          '*'
        );
        return;
      }

      // ── Step 11.5: product listing request ──
      if (data.type === 'REVIEWLENS_GET_LISTING') {
        var listing = extractProductListing();
        window.postMessage(
          {
            type: 'REVIEWLENS_LISTING_RESPONSE',
            requestId: data.requestId,
            listing: listing,
          },
          '*'
        );
        return;
      }

      // ── Step 11.5: variation ASINs request ──
      if (data.type === 'REVIEWLENS_GET_VARIATIONS') {
        var variations = extractVariationAsins();
        window.postMessage(
          {
            type: 'REVIEWLENS_VARIATIONS_RESPONSE',
            requestId: data.requestId,
            variations: variations,
          },
          '*'
        );
        return;
      }
    });

    // Initial extraction + start observer after DOM settles
    // Only start MutationObserver on review pages to avoid spurious warnings
    setTimeout(function () {
      handleNewDOM();
      if (detectPageType() === 'reviews') {
        startObserver();
      }
    }, 1000);

    console.log('[ReviewLens MAIN] window.__REVIEWLENS__ ready ✓');
  } catch (e) {
    console.error('[ReviewLens MAIN] Injection error:', e);
  }
})();
