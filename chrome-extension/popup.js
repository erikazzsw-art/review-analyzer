/**
 * ClueAI ReviewLens — Popup Script
 *
 * Step 13: One-click review scraping, progress display, CSV export.
 * Step 14-1: Degradation detection UI — shows page structure change warnings.
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

  // Step 14-1: Degradation UI elements
  const degradeSection = document.getElementById('degradeSection');
  const degradeNotice = document.getElementById('degradeNotice');
  const degradeIcon = document.getElementById('degradeIcon');
  const degradeText = document.getElementById('degradeText');
  const feedbackLink = document.getElementById('feedbackLink');

  // ── State ──
  let isScraping = false;
  let currentPageInfo = null;

  // ── Initialization ──
  try {
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
          actionHint.textContent =
            '✅ 本页抓取 ' + result.new_reviews + ' 条（累计 ' + result.total_reviews + ' 条）。翻页后请再次点击抓取。';
          actionHint.className = 'action-hint action-hint--info';
        } else if (result.total_reviews > 0) {
          actionHint.textContent =
            '📋 未发现新评论（已累计 ' + result.total_reviews + ' 条）。翻页后请再次点击抓取。';
          actionHint.className = 'action-hint';
        } else {
          // Step 14-1: degraded=false but 0 reviews — gentle reminder
          actionHint.textContent =
            'ℹ️ 当前页面未检测到评论。如果您确认在评论页，请尝试刷新后重试。';
          actionHint.className = 'action-hint action-hint--muted';
          scrapeBtn.disabled = false;
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
 * Trigger review scraping on the active tab
 */
async function startScraping() {
  return new Promise((resolve, reject) => {
    try {
      if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
        reject(new Error('chrome.runtime.sendMessage not available'));
        return;
      }
      chrome.runtime.sendMessage({ type: 'START_SCRAPING' }, (response) => {
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
    degradeText.textContent =
      '此页面评论结构已变化，扩展暂无法提取。我们会尽快适配。';
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
    degradeText.textContent =
      '产品页未检测到评论列表。请切换到评论页（/product-reviews/...）后重试。';
    feedbackLink.hidden = true;
  } else {
    // Other pages (amazon_other, not_amazon, etc.)
    degradeNotice.className = 'degrade-notice degrade-notice--info';
    degradeIcon.textContent = 'ℹ️';
    degradeText.textContent = '当前页面不支持评论提取，请前往 Amazon 评论页面。';
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
  scrapeBtn.textContent = '📥 抓取评论';

  const pageType = pageInfo.pageType || 'reviews';

  if (pageType === 'reviews') {
    actionHint.textContent = '';
  } else if (pageType === 'product') {
    actionHint.textContent = '';
  } else {
    actionHint.textContent = '请前往 Amazon 评论页面使用此功能';
    actionHint.className = 'action-hint action-hint--muted';
  }
}
