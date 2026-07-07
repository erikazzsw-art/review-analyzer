import { defineRouting } from "next-intl/routing";

// URL 层策略：locale 不进 URL（localePrefix: "never"），完全靠 middleware + cookie 驱动
// 原因见 PROGRESS_V2.md V4-出海-M2.1（路线 A）
// defaultLocale = "en" —— 主打出海，默认英文，中国用户由 middleware 检测或手动切换
export const routing = defineRouting({
  locales: ["zh", "en"],
  defaultLocale: "en",
  localeDetection: true,
  localeCookie: {
    name: "NEXT_LOCALE",
  },
  localePrefix: "never",
  // 关掉 <link rel="alternate" hreflang> 自动注入 —— URL 单一时会指向同一 URL，反而误导 SEO
  alternateLinks: false,
});
