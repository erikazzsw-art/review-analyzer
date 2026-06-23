"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Check, Globe } from "lucide-react";

import { routing } from "@/i18n/routing";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type LocaleSwitcherProps = {
  variant?: "header" | "sidebar";
};

type LocaleCode = "zh" | "en";

const LOCALE_OPTIONS: { code: LocaleCode; labelKey: "zh" | "en" }[] = [
  { code: "zh", labelKey: "zh" },
  { code: "en", labelKey: "en" },
];

export function LocaleSwitcher({ variant = "header" }: LocaleSwitcherProps) {
  const t = useTranslations("locale");
  const locale = useLocale() as LocaleCode;
  const [isSwitching, setIsSwitching] = useState(false);

  function handleSelect(next: LocaleCode) {
    if (isSwitching || next === locale) return;
    setIsSwitching(true);
    const cookieName = typeof routing.localeCookie === "object" && routing.localeCookie
      ? routing.localeCookie.name
      : "NEXT_LOCALE";
    document.cookie = `${cookieName}=${next};path=/;max-age=31536000;samesite=lax`;
    window.location.reload();
  }

  const triggerClass =
    variant === "sidebar"
      ? "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-soft transition hover:bg-roseSoft/40 hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-rose/50 disabled:opacity-50"
      : "inline-flex items-center gap-1.5 rounded-pill border border-line bg-white/70 px-3 py-1.5 text-xs font-semibold text-soft backdrop-blur transition hover:border-[#d8cfde] hover:bg-white hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-rose/50 disabled:opacity-50";

  const iconSize = variant === "sidebar" ? "h-4 w-4" : "h-3.5 w-3.5";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          disabled={isSwitching}
          aria-label={t("switchLanguage")}
          className={triggerClass}
        >
          <Globe className={iconSize} />
          {variant === "sidebar" && (
            <span className="flex-1 text-left">{t(locale)}</span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align={variant === "sidebar" ? "start" : "end"}
        side={variant === "sidebar" ? "top" : "bottom"}
        sideOffset={8}
        className="min-w-[140px] rounded-xl border border-line bg-white p-1 shadow-card"
      >
        {LOCALE_OPTIONS.map((opt) => {
          const isActive = opt.code === locale;
          return (
            <DropdownMenuItem
              key={opt.code}
              onSelect={(e) => {
                e.preventDefault();
                handleSelect(opt.code);
              }}
              className="cursor-pointer gap-2 rounded-md px-3 py-2 text-sm text-ink hover:bg-roseSoft/50 focus:bg-roseSoft/50"
            >
              <span className="flex-1">{t(opt.labelKey)}</span>
              {isActive && <Check className="h-4 w-4 text-rose" />}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}