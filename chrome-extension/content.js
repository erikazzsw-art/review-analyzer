/**
 * ClueAI ReviewLens — Content Script
 *
 * Injected into Amazon product/review pages.
 * Step 10 (current): detect page type and report to service worker.
 * Future steps: DOM parsing for review extraction, pagination handling, etc.
 */

(function () {
  'use strict';

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
    // Examples:
    //   amazon.com/dp/B0ABCD1234
    //   amazon.com/Some-Product-Name/dp/B0ABCD1234
    if (/\/dp\/[A-Z0-9]{10}/i.test(url)) {
      return 'product';
    }

    // Review page: /product-reviews/<ASIN>
    // Example: amazon.com/product-reviews/B0ABCD1234
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
      // Service worker may not be ready yet; that's fine for now
    });

  // Listen for detection requests from popup (via service worker)
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.type === 'DETECT_PAGE') {
      sendResponse({
        pageType: detectPageType(),
        url: window.location.href,
        title: document.title,
      });
      return true;
    }
  });

  console.log('[ReviewLens CS] Content script loaded —', pageType);
})();
