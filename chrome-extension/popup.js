/**
 * ClueAI ReviewLens — Popup Script
 *
 * Step 10: Display current page type + placeholder "抓取评论" button.
 * Future steps: trigger scraping, show progress, display results summary.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const pageTypeBadge = document.getElementById('pageTypeBadge');
  const pageUrl = document.getElementById('pageUrl');
  const scrapeBtn = document.getElementById('scrapeBtn');
  const actionHint = document.getElementById('actionHint');

  // ── Detect current page ──
  try {
    const pageInfo = await getPageInfo();

    updatePageTypeUI(pageInfo);
    updateActionUI(pageInfo);
  } catch (err) {
    console.error('[ReviewLens Popup] Error:', err);
    pageTypeBadge.textContent = '检测失败';
    pageTypeBadge.className = 'badge badge--error';
    pageUrl.textContent = '无法获取页面信息，请刷新后重试';
    scrapeBtn.disabled = true;
    actionHint.textContent = '';
  }

  // ── Button click handler ──
  scrapeBtn.addEventListener('click', () => {
    scrapeBtn.disabled = true;
    scrapeBtn.textContent = '⏳ 功能开发中…';
    actionHint.textContent = '评论抓取功能即将上线，敬请期待！';
    actionHint.className = 'action-hint action-hint--info';

    // Re-enable after brief feedback
    setTimeout(() => {
      scrapeBtn.disabled = false;
      scrapeBtn.textContent = '📥 抓取评论';
      actionHint.textContent = '';
    }, 3000);
  });
});

/**
 * Query page info for the active tab via service worker
 */
async function getPageInfo() {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: 'GET_PAGE_INFO' }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response || { pageType: 'unknown', url: null });
    });
  });
}

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
    urlEl.textContent = '非 Amazon 页面';
  }

  // Set badge
  switch (pageInfo.pageType) {
    case 'product':
      badge.textContent = '📦 产品页面';
      badge.className = 'badge badge--product';
      break;
    case 'reviews':
      badge.textContent = '💬 评论页面';
      badge.className = 'badge badge--reviews';
      break;
    case 'amazon_other':
      badge.textContent = '🌐 Amazon 其他页面';
      badge.className = 'badge badge--other';
      break;
    case 'not_amazon':
      badge.textContent = '❌ 非 Amazon 页面';
      badge.className = 'badge badge--not-amazon';
      break;
    case 'unknown':
    default:
      badge.textContent = '❓ 未知页面';
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
    scrapeBtn.textContent = '📥 抓取评论';
    actionHint.textContent = '点击按钮抓取当前页面的评论数据';
    actionHint.className = 'action-hint';
  } else if (pageInfo.pageType === 'not_amazon') {
    scrapeBtn.disabled = true;
    scrapeBtn.textContent = '📥 抓取评论';
    actionHint.textContent = '请前往 Amazon 产品页面或评论页面使用此功能';
    actionHint.className = 'action-hint action-hint--muted';
  } else if (pageInfo.pageType === 'amazon_other') {
    scrapeBtn.disabled = true;
    scrapeBtn.textContent = '📥 抓取评论';
    actionHint.textContent = '请前往 Amazon 产品详情页（/dp/...）或评论页面';
    actionHint.className = 'action-hint action-hint--muted';
  } else {
    scrapeBtn.disabled = true;
    actionHint.textContent = '';
  }
}
