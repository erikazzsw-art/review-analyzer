import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

type Locale = "zh" | "en";

const SUPPORTED_LOCALES: readonly Locale[] = ["zh", "en"] as const;
// 与 i18n/routing.ts 的 defaultLocale 保持一致：主打出海，默认英文
const DEFAULT_LOCALE: Locale = "en";
const COOKIE_NAME = "NEXT_LOCALE";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1 年

// Cloudflare CF-IPCountry 头返回的 ISO 3166-1 alpha-2 国家码
// 命中即视为英文优先市场（M2 出海白名单：北美 + 主要英语国家）
const EN_PRIORITY_COUNTRIES = new Set([
  "US",
  "CA",
  "GB",
  "UK",
  "AU",
  "NZ",
  "IE",
  "SG",
]);

/**
 * 解析 Accept-Language header 找出首选语言。
 * 只识别 zh / en 前缀，忽略 q 权重（简化实现，符合 90% 场景）。
 */
function detectFromAcceptLanguage(header: string | null): Locale | null {
  if (!header) return null;
  const first = header
    .split(",")
    .map((entry) => entry.trim().toLowerCase().split(";")[0])
    .find((tag) => tag.startsWith("zh") || tag.startsWith("en"));
  if (!first) return null;
  return first.startsWith("zh") ? "zh" : "en";
}

/**
 * 按优先级检测首次访问用户的 locale：
 * 1. CF-IPCountry（Cloudflare 边缘注入的地理国家）—— 命中英语市场白名单则 en
 * 2. Accept-Language 浏览器语言 —— 明确 zh-* 则 zh，明确 en-* 则 en
 * 3. 默认 en（主打出海）
 */
function detectLocale(request: NextRequest): Locale {
  const country = request.headers.get("cf-ipcountry")?.toUpperCase();
  if (country && EN_PRIORITY_COUNTRIES.has(country)) {
    return "en";
  }
  // 中国大陆 IP 显式回落 zh，不受下面 Accept-Language 影响（部分 Chrome 默认 en-US）
  if (country === "CN" || country === "HK" || country === "MO" || country === "TW") {
    return "zh";
  }

  const fromHeader = detectFromAcceptLanguage(request.headers.get("accept-language"));
  if (fromHeader) return fromHeader;

  return DEFAULT_LOCALE;
}

export function middleware(request: NextRequest) {
  const response = NextResponse.next();

  const existing = request.cookies.get(COOKIE_NAME)?.value;
  const isSupported = existing && (SUPPORTED_LOCALES as readonly string[]).includes(existing);

  const locale: Locale = isSupported ? (existing as Locale) : detectLocale(request);

  // 首次访问或 cookie 值非法时写回 cookie，用户已选则尊重
  if (!isSupported) {
    response.cookies.set(COOKIE_NAME, locale, {
      path: "/",
      sameSite: "lax",
      maxAge: COOKIE_MAX_AGE,
    });
  }

  // 让搜索引擎和 CDN 知道当前响应语言 + 按 cookie 分片缓存
  response.headers.set("Content-Language", locale === "zh" ? "zh-CN" : "en-US");
  const existingVary = response.headers.get("Vary");
  const varyValue = existingVary ? `${existingVary}, Cookie` : "Cookie";
  response.headers.set("Vary", varyValue);
  response.headers.set("Cache-Control", "private, no-store, max-age=0, must-revalidate");

  return response;
}

export const config = {
  matcher: [
    "/((?!api|_next|fonts|favicon.ico|.*\\..*).*)",
  ],
};
