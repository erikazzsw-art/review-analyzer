/**
 * ClueAI ReviewLens — Popup Script
 *
 * Step 13: One-click review scraping, progress display, CSV export.
 * Communicates with background service worker for all operations.
 */

document.addEventListener('DOMContentLoaded', async () => {
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

  // ── State ──
  let isScraping = false;
  let currentPageInfo = null;

  // ── Initialization ──
  try {
    // 1. Detect page type
    currentPageInfo = await getPageInfo();
    updatePageTypeUI(currentPageInfo);
    updateActionUI(currentPageInfo);

    // 2. Check if reviews already exist for this tab
    const status = await getScrapeStatus();
    if (status.total_reviews > 0) {
      updateProgressUI(status.total_reviews);
      showExportUI(true);
      updateHintForExistingReviews(status.total_reviews);
    }
  } catch (err) {
    console.error('[ReviewLens Popup] Init error:', err);
    pageTypeBadge.textContent = '检测失败';
    pageTypeBadge.className = 'badge badge--error';
    pageUrl.textContent = '无法获取页面信息，请刷新后重试';
    scrapeBtn.disabled = true;
  }

  // ── Scrape button ──
  scrapeBtn.addEventListener('click', async () => {
    if (isScraping) return;

    isScraping = true;
    setScrapingUI(true);

    try {
      const result = await startScraping();

      if (result.success) {
        updateProgressUI(result.total_reviews);
        showExportUI(true);

        if (result.new_reviews > 0) {
          actionHint.textContent =
            '✅ 本页抓取 ' + result.new_reviews + ' 条（累计 ' + result.total_reviews + ' 条）。翻页后请再次点击抓取。';
          actionHint.className = 'action-hint action-hint--info';
        } else if (result.total_reviews > 0) {
          actionHint.textContent =
            '📋 未发现新评论（已累计 ' + result.total_reviews + ' 条）。翻页后请再次点击抓取。';
          actionHint.className = 'action-hint';
        } else {
          actionHint.textContent = '⚠️ 当前页面未检测到评论。请确认您在 Amazon 评论页面。';
          actionHint.className = 'action-hint action-hint--muted';
        }
      } else {
        actionHint.textContent = '❌ 抓取失败：' + (result.error || '未知错误');
        actionHint.className = 'action-hint action-hint--muted';
      }
    } catch (err) {
      console.error('[ReviewLens Popup] Scrape error:', err);
      actionHint.textContent = '❌ 抓取失败：' + (err.message || '未知错误');
      actionHint.className = 'action-hint action-hint--muted';
    } finally {
      isScraping = false;
      setScrapingUI(false);
    }
  });

  // ── Export button ──
  exportBtn.addEventListener('click', async () => {
    exportBtn.disabled = true;
    exportBtn.textContent = '⏳ 导出中…';

    try {
      const result = await exportCsv();
      if (result.success) {
        actionHint.textContent =
          '✅ 已导出 ' + result.total_exported + ' 条评论到 ' + result.filename;
        actionHint.className = 'action-hint action-hint--info';
        exportBtn.textContent = '✅ 导出完成';
        setTimeout(() => {
          exportBtn.textContent = '📥 导出 CSV';
          exportBtn.disabled = false;
        }, 2000);
      } else {
        actionHint.textContent = '❌ 导出失败：' + (result.error || '未知错误');
        actionHint.className = 'action-hint action-hint--muted';
        exportBtn.textContent = '📥 导出 CSV';
        exportBtn.disabled = false;
      }
    } catch (err) {
      console.error('[ReviewLens Popup] Export error:', err);
      actionHint.textContent = '❌ 导出失败：' + (err.message || '未知错误');
      actionHint.className = 'action-hint action-hint--muted';
      exportBtn.textContent = '📥 导出 CSV';
      exportBtn.disabled = false;
    }
  });

  // ── Reset button ──
  resetBtn.addEventListener('click', async () => {
    resetBtn.disabled = true;
    resetBtn.textContent = '⏳ 清除中…';

    try {
      await clearReviews();
      updateProgressUI(0);
      showExportUI(false);
      actionHint.textContent = '数据已清除。点击按钮重新抓取评论。';
      actionHint.className = 'action-hint';
      resetBtn.textContent = '🗑 清除数据';
      resetBtn.disabled = false;
    } catch (err) {
      console.error('[ReviewLens Popup] Clear error:', err);
      resetBtn.textContent = '🗑 清除数据';
      resetBtn.disabled = false;
    }
  });

  // ── UI helpers ──

  function setScrapingUI(active) {
    if (active) {
      scrapeBtn.disabled = true;
      scrapeBtn.textContent = '⏳ 抓取中…';
    } else {
      scrapeBtn.disabled = false;
      scrapeBtn.textContent = '🔄 继续抓取';
    }
  }

  function updateProgressUI(total) {
    progressCount.textContent = total + ' 条';
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
      exportBtn.textContent = '📥 导出 CSV';
    }
  }

  function updateHintForExistingReviews(total) {
    scrapeBtn.textContent = '🔄 继续抓取';
    actionHint.textContent =
      '已抓取 ' + total + ' 条评论。翻页后点击按钮追加更多。';
    actionHint.className = 'action-hint action-hint--info';
  }
});

// ═══════════════════════════════════════════════════════════════
// Background communication
// ═══════════════════════════════════════════════════════════════

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
 * Get current scrape status (stored reviews) for active tab
 */
async function getScrapeStatus() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: 'GET_SCRAPE_STATUS' }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('[ReviewLens Popup] getScrapeStatus error:', chrome.runtime.lastError);
        resolve({ total_reviews: 0, reviews: [], page_info: null });
        return;
      }
      resolve(response || { total_reviews: 0, reviews: [], page_info: null });
    });
  });
}

/**
 * Trigger review scraping on the active tab
 */
async function startScraping() {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: 'START_SCRAPING' }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response || { success: false, error: 'no_response' });
    });
  });
}

/**
 * Export accumulated reviews as CSV file
 */
async function exportCsv() {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: 'EXPORT_CSV' }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response || { success: false, error: 'no_response' });
    });
  });
}

/**
 * Clear accumulated reviews for active tab
 */
async function clearReviews() {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: 'CLEAR_REVIEWS' }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      resolve(response || { success: false });
    });
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
