import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  // 优先用 next-intl 注入的 requestLocale，没有则回退到 NEXT_LOCALE cookie
  let locale = await requestLocale;

  if (!locale) {
    const cookieStore = await cookies();
    const cookieLocale = cookieStore.get("NEXT_LOCALE")?.value;
    if (cookieLocale) {
      locale = cookieLocale;
    }
  }

  if (!locale || !routing.locales.includes(locale as "zh" | "en")) {
    locale = routing.defaultLocale;
  }

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
