import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["zh", "en"],
  defaultLocale: "zh",
  localeDetection: true,
  localeCookie: {
    name: "NEXT_LOCALE",
  },
  localePrefix: "never",
});
