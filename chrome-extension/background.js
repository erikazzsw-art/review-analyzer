/**
 * ClueAI ReviewLens — Background Service Worker
 *
 * Manifest V3 service worker.
 * Coordinates communication between popup and content scripts.
 * In future steps: handles scraping orchestration, CSV generation, download triggers.
 */

// Store the latest page info reported by content scripts, keyed by tabId
const tabPageInfo = new Map();

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
            });
            return;
          }

          // Fallback: detect from tab URL
          sendResponse({
            pageType: detectPageTypeFromUrl(tab.url || ''),
            url: tab.url || '',
            source: 'url_fallback',
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

// Clean up stale tab info when tabs close
chrome.tabs.onRemoved.addListener((tabId) => {
  tabPageInfo.delete(tabId);
});

console.log('[ReviewLens BG] Service worker registered');
