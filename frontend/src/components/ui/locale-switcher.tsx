"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { Globe } from "lucide-react";

import { routing } from "@/i18n/routing";

type LocaleSwitcherProps = {
  variant?: "header" | "sidebar";
};

export function LocaleSwitcher({ variant = "header" }: LocaleSwitcherProps) {
  const t = useTranslations("locale");
  const locale = useLocale();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function handleSwitch() {
    const nextLocale = locale === "zh" ? "en" : "zh";
    const cookieName = typeof routing.localeCookie === "object" && routing.localeCookie
      ? routing.localeCookie.name
      : "NEXT_LOCALE";
    document.cookie = `${cookieName}=${nextLocale};path=/;max-age=31536000;samesite=lax`;
    startTransition(() => {
      router.refresh();
    });
  }

  if (variant === "sidebar") {
    return (
      <button
        type="button"
        onClick={handleSwitch}
        disabled={isPending}
        className="flex w-full items-center gap-2 rounded-pill px-3 py-2 text-sm font-medium text-soft transition hover:bg-white/80 hover:text-ink disabled:opacity-50"
      >
        <Globe className="h-4 w-4" />
        <span>{t("switchTo")}</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleSwitch}
      disabled={isPending}
      className="inline-flex items-center gap-1.5 rounded-pill border border-line bg-white/70 px-3 py-1.5 text-xs font-semibold text-soft backdrop-blur transition hover:border-[#d8cfde] hover:bg-white hover:text-ink disabled:opacity-50"
    >
      <Globe className="h-3.5 w-3.5" />
      <span>{t("switchTo")}</span>
    </button>
  );
}
