/**
 * ClueAI ReviewLens — i18n module (Step 16)
 *
 * Lightweight bilingual (zh-CN / en-US) message dictionary for the popup.
 *
 * Why not chrome.i18n / _locales?
 *   The popup builds most user-facing strings via runtime concatenation
 *   (counts, countdown seconds, error suffixes). chrome.i18n only resolves
 *   __MSG_x__ placeholders in static HTML/CSS/manifest — it can't help with
 *   the dynamic strings that dominate this popup. A small JS dictionary with
 *   parameter interpolation covers both static labels and dynamic messages,
 *   and lets the user flip languages live without reloading the extension.
 *
 * Usage:
 *   await I18N.init();                 // load saved locale from storage
 *   I18N.t('scrape_btn');              // → "抓取评论" / "Scrape reviews"
 *   I18N.t('scrape_done', {n: 5, total: 20});  // interpolates {n} / {total}
 *   await I18N.setLocale('en-US');     // persist + switch
 */

(function (global) {
  'use strict';

  var STORAGE_KEY = 'uiLocale';
  var DEFAULT_LOCALE = 'zh-CN';
  var SUPPORTED = ['zh-CN', 'en-US'];

  var MESSAGES = {
    'zh-CN': {
      // ── Header / footer ──
      app_title: 'ClueAI ReviewLens',
      footer_link: 'ClueAI ReviewLens',
      lang_toggle_label: 'EN',
      lang_toggle_title: 'Switch to English',

      // ── Login section ──
      login_checking: '检测登录状态…',
      login_logged_in: '已登录：{username}',
      login_plan: '{plan} 套餐',
      login_logged_out: '未登录',
      login_btn: '去登录',
      login_hint_required: '请先登录 clueai-reviewlens.com 再上传',

      // ── Page status ──
      status_page_label: '当前页面',
      badge_detecting: '检测中…',
      badge_product: '📦 产品页面',
      badge_reviews: '💬 评论页面',
      badge_amazon_other: '🌐 Amazon 其他页面',
      badge_not_amazon: '❌ 非 Amazon 页面',
      badge_unknown: '❓ 未知页面',
      badge_detect_failed: '检测失败',
      page_not_amazon: '非 Amazon 页面',
      detect_failed_hint: '无法获取页面信息，请刷新后重试',

      // ── Actions ──
      scrape_btn: '📥 抓取评论',
      scrape_btn_continue: '🔄 继续抓取',
      scrape_btn_scraping: '⏳ 抓取中…',
      scrape_btn_wait: '⏳ 等待 {n} 秒',
      export_btn: '📥 导出 CSV',
      export_btn_exporting: '⏳ 导出中…',
      export_btn_done: '✅ 导出完成',
      upload_btn: '☁️ 上传到 ClueAI',
      upload_btn_uploading: '⏳ 上传中…',
      upload_btn_done: '✅ 上传完成',
      reset_btn: '🗑 清除数据',
      reset_btn_clearing: '⏳ 清除中…',
      feedback_link: '📋 反馈此页面',

      // ── Hints ──
      hint_click_to_scrape: '点击按钮抓取当前页面的评论数据',
      hint_goto_amazon: '请前往 Amazon 产品页面或评论页面使用此功能',
      hint_goto_product: '请前往 Amazon 产品详情页（/dp/...）或评论页面',
      hint_goto_reviews: '请前往 Amazon 评论页面使用此功能',
      hint_existing: '已抓取 {total} 条评论。翻页后点击按钮追加更多。',
      progress_label: '已抓取',
      progress_count: '{n} 条',

      // ── Scrape results ──
      scrape_done_new: '✅ 本页抓取 {n} 条（累计 {total} 条）。翻页后请再次点击抓取。',
      scrape_no_new: '📋 未发现新评论（已累计 {total} 条）。翻页后请再次点击抓取。',
      scrape_zero_page: 'ℹ️ 当前页面未检测到评论。如果您确认在评论页，请尝试刷新后重试。',
      scrape_failed: '❌ 抓取失败：{msg}',
      scrape_timeout: '后台响应超时，请重试',
      err_unknown: '未知错误',
      // Fix #3: storage quota exceeded warning
      storage_quota_warning: '⚠️ 存储空间不足，评论数量已达上限。请先上传已有评论再继续抓取。',

      // ── Export / upload results ──
      export_done: '✅ 已导出 {n} 条评论到 {filename}',
      export_failed: '❌ 导出失败：{msg}',
      upload_done: '✓ 上传成功：{n} 条新评论（跳过 {dup} 条重复）',
      upload_failed: '❌ 上传失败：{msg}',
      upload_err_api: 'API 返回错误，请稍后重试',
      upload_err_network: '网络错误，无法连接服务器',
      upload_err_no_reviews: '当前没有可上传的评论',
      reset_done: '数据已清除。点击按钮重新抓取评论。',

      // ── Degradation ──
      degrade_reviews: '此页面评论结构已变化，扩展暂无法提取。我们会尽快适配。',
      degrade_product: '产品页未检测到评论列表。请切换到评论页（/product-reviews/...）后重试。',
      degrade_other: '当前页面不支持评论提取，请前往 Amazon 评论页面。',

      // ── Anti-crawl ──
      anticrawl_captcha: '检测到验证码。Amazon 已限制当前页面的自动抓取。请手动完成验证码后刷新页面重试。',
      anticrawl_throttle: '抓取过于频繁，请等待 {n} 秒后重试。',
      anticrawl_zeros: '连续 {n} 次未提取到评论。可能触发了 Amazon 反爬限制，建议等待 5 分钟后重试。',

      // ── Listing tab (Step 11.5) ──
      tab_listing: '📊 产品信息',
      tab_reviews: '💬 评论',
      listing_name_label: '产品名称',
      listing_name_placeholder: '请输入产品名称（如：XX品牌蓝牙耳机）',
      listing_name_required: '请先输入产品名称',
      listing_scrape_btn: '🔍 提取产品信息',
      listing_scrape_btn_scraping: '⏳ 提取中…',
      listing_scrape_btn_redo: '🔄 重新提取',
      listing_scrape_done: '✅ 产品信息提取完成，请填写产品名称后上传',
      listing_scrape_failed: '❌ 提取失败：{msg}',
      listing_hint_click: '点击按钮提取当前产品页面的信息',
      listing_hint_not_product: '请前往 Amazon 产品详情页（/dp/...）使用此功能',
      listing_preview_title: '📋 抓取结果预览',
      listing_no_data: '暂无数据',
      listing_upload_btn: '☁️ 上传到产品管理',
      listing_upload_btn_uploading: '⏳ 上传中…',
      listing_upload_btn_done: '✅ 已上传',
      listing_upload_success: '上传成功！',
      listing_upload_done_hint: '产品信息已上传到产品管理页面',
      listing_view_product: '查看产品 →',
      reviews_page_link: '💬 前往评论页抓取',
      listing_field_title: '标题',
      listing_field_price: '价格',
      listing_field_rating: '评分',
      listing_field_ratings: '评',
      listing_field_brand: '品牌',
      listing_field_marketplace: '站点',
      listing_field_bullets: '卖点',
      listing_field_items: '项',
      listing_field_variants: '变体',
      listing_field_desc: '描述',
      listing_more_variants: '还有 {n} 个变体',
    },

    'en-US': {
      // ── Header / footer ──
      app_title: 'ClueAI ReviewLens',
      footer_link: 'ClueAI ReviewLens',
      lang_toggle_label: '中',
      lang_toggle_title: '切换到中文',

      // ── Login section ──
      login_checking: 'Checking login…',
      login_logged_in: 'Signed in: {username}',
      login_plan: '{plan} plan',
      login_logged_out: 'Not signed in',
      login_btn: 'Sign in',
      login_hint_required: 'Please sign in to clueai-reviewlens.com before uploading',

      // ── Page status ──
      status_page_label: 'Current page',
      badge_detecting: 'Detecting…',
      badge_product: '📦 Product page',
      badge_reviews: '💬 Reviews page',
      badge_amazon_other: '🌐 Other Amazon page',
      badge_not_amazon: '❌ Not an Amazon page',
      badge_unknown: '❓ Unknown page',
      badge_detect_failed: 'Detection failed',
      page_not_amazon: 'Not an Amazon page',
      detect_failed_hint: 'Could not read page info. Refresh and try again.',

      // ── Actions ──
      scrape_btn: '📥 Scrape reviews',
      scrape_btn_continue: '🔄 Scrape more',
      scrape_btn_scraping: '⏳ Scraping…',
      scrape_btn_wait: '⏳ Wait {n}s',
      export_btn: '📥 Export CSV',
      export_btn_exporting: '⏳ Exporting…',
      export_btn_done: '✅ Exported',
      upload_btn: '☁️ Upload to ClueAI',
      upload_btn_uploading: '⏳ Uploading…',
      upload_btn_done: '✅ Uploaded',
      reset_btn: '🗑 Clear data',
      reset_btn_clearing: '⏳ Clearing…',
      feedback_link: '📋 Report this page',

      // ── Hints ──
      hint_click_to_scrape: 'Click to scrape reviews from the current page',
      hint_goto_amazon: 'Open an Amazon product or reviews page to use this',
      hint_goto_product: 'Open an Amazon product page (/dp/...) or reviews page',
      hint_goto_reviews: 'Open an Amazon reviews page to use this',
      hint_existing: '{total} reviews scraped. Turn the page and click again to add more.',
      progress_label: 'Scraped',
      progress_count: '{n}',

      // ── Scrape results ──
      scrape_done_new: '✅ Scraped {n} on this page ({total} total). Turn the page and scrape again.',
      scrape_no_new: '📋 No new reviews found ({total} total). Turn the page and scrape again.',
      scrape_zero_page: 'ℹ️ No reviews detected on this page. If you are on a reviews page, refresh and retry.',
      scrape_failed: '❌ Scrape failed: {msg}',
      scrape_timeout: 'Background timed out, please retry',
      err_unknown: 'Unknown error',
      // Fix #3: storage quota exceeded warning
      storage_quota_warning: '⚠️ Storage quota exceeded — review limit reached. Upload existing reviews before continuing.',

      // ── Export / upload results ──
      export_done: '✅ Exported {n} reviews to {filename}',
      export_failed: '❌ Export failed: {msg}',
      upload_done: '✓ Uploaded: {n} new reviews ({dup} duplicates skipped)',
      upload_failed: '❌ Upload failed: {msg}',
      upload_err_api: 'API returned an error, please retry later',
      upload_err_network: 'Network error, could not reach the server',
      upload_err_no_reviews: 'No reviews to upload',
      reset_done: 'Data cleared. Click to scrape reviews again.',

      // ── Degradation ──
      degrade_reviews: 'This page’s review layout has changed and can’t be extracted yet. We’ll adapt soon.',
      degrade_product: 'No review list on the product page. Switch to the reviews page (/product-reviews/...) and retry.',
      degrade_other: 'Review extraction is not supported on this page. Open an Amazon reviews page.',

      // ── Anti-crawl ──
      anticrawl_captcha: 'CAPTCHA detected. Amazon has blocked automatic scraping on this page. Solve it manually, refresh, and retry.',
      anticrawl_throttle: 'Scraping too fast. Please wait {n}s and retry.',
      anticrawl_zeros: 'No reviews extracted {n} times in a row. Amazon anti-bot limits may be active — wait 5 minutes and retry.',

      // ── Listing tab (Step 11.5) ──
      tab_listing: '📊 Product Info',
      tab_reviews: '💬 Reviews',
      listing_name_label: 'Product name',
      listing_name_placeholder: 'Enter product name (e.g. Brand Bluetooth Headphones)',
      listing_name_required: 'Please enter a product name',
      listing_scrape_btn: '🔍 Extract Product Info',
      listing_scrape_btn_scraping: '⏳ Extracting…',
      listing_scrape_btn_redo: '🔄 Re-extract',
      listing_scrape_done: '✅ Product info extracted. Enter a name and upload.',
      listing_scrape_failed: '❌ Extraction failed: {msg}',
      listing_hint_click: 'Click to extract product info from this page',
      listing_hint_not_product: 'Open an Amazon product page (/dp/...) to use this feature',
      listing_preview_title: '📋 Extraction Preview',
      listing_no_data: 'No data',
      listing_upload_btn: '☁️ Upload to Product Manager',
      listing_upload_btn_uploading: '⏳ Uploading…',
      listing_upload_btn_done: '✅ Uploaded',
      listing_upload_success: 'Upload successful!',
      listing_upload_done_hint: 'Product info has been uploaded to Product Manager',
      listing_view_product: 'View Product →',
      reviews_page_link: '💬 Open Reviews Page',
      listing_field_title: 'Title',
      listing_field_price: 'Price',
      listing_field_rating: 'Rating',
      listing_field_ratings: 'ratings',
      listing_field_brand: 'Brand',
      listing_field_marketplace: 'Market',
      listing_field_bullets: 'Bullets',
      listing_field_items: 'items',
      listing_field_variants: 'Variants',
      listing_field_desc: 'Description',
      listing_more_variants: '{n} more variants',
    },
  };

  var currentLocale = DEFAULT_LOCALE;

  function normalize(locale) {
    if (!locale) return DEFAULT_LOCALE;
    if (SUPPORTED.indexOf(locale) !== -1) return locale;
    // Match language prefix: "en", "en-GB" → "en-US"; "zh", "zh-TW" → "zh-CN"
    var prefix = String(locale).toLowerCase().split('-')[0];
    if (prefix === 'en') return 'en-US';
    if (prefix === 'zh') return 'zh-CN';
    return DEFAULT_LOCALE;
  }

  function interpolate(template, params) {
    if (!params) return template;
    return template.replace(/\{(\w+)\}/g, function (match, key) {
      return Object.prototype.hasOwnProperty.call(params, key)
        ? String(params[key])
        : match;
    });
  }

  var I18N = {
    /** Load saved locale from storage; fall back to browser UI language. */
    init: function () {
      return new Promise(function (resolve) {
        try {
          if (typeof chrome === 'undefined' || !chrome.storage?.local) {
            currentLocale = DEFAULT_LOCALE;
            resolve(currentLocale);
            return;
          }
          chrome.storage.local.get(STORAGE_KEY, function (data) {
            if (data && data[STORAGE_KEY]) {
              currentLocale = normalize(data[STORAGE_KEY]);
            } else {
              // No saved choice → derive from browser UI language
              var uiLang = (typeof chrome.i18n?.getUILanguage === 'function')
                ? chrome.i18n.getUILanguage()
                : (global.navigator && global.navigator.language) || DEFAULT_LOCALE;
              currentLocale = normalize(uiLang);
            }
            resolve(currentLocale);
          });
        } catch (_) {
          currentLocale = DEFAULT_LOCALE;
          resolve(currentLocale);
        }
      });
    },

    /** Persist and switch the active locale. */
    setLocale: function (locale) {
      currentLocale = normalize(locale);
      return new Promise(function (resolve) {
        try {
          if (chrome.storage?.local) {
            chrome.storage.local.set({ [STORAGE_KEY]: currentLocale }, function () {
              resolve(currentLocale);
            });
            return;
          }
        } catch (_) { /* fall through */ }
        resolve(currentLocale);
      });
    },

    getLocale: function () {
      return currentLocale;
    },

    /** Toggle between the two supported locales, persisting the result. */
    toggle: function () {
      var next = currentLocale === 'zh-CN' ? 'en-US' : 'zh-CN';
      return this.setLocale(next);
    },

    /** Translate a key with optional {param} interpolation. */
    t: function (key, params) {
      var table = MESSAGES[currentLocale] || MESSAGES[DEFAULT_LOCALE];
      var template = table[key];
      if (template === undefined) {
        // Fall back to default locale, then to the raw key
        template = (MESSAGES[DEFAULT_LOCALE][key] !== undefined)
          ? MESSAGES[DEFAULT_LOCALE][key]
          : key;
      }
      return interpolate(template, params);
    },
  };

  global.I18N = I18N;
})(typeof window !== 'undefined' ? window : this);
