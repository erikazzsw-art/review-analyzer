"use client";

import { useEffect, useState } from "react";
import { useTranslations, useMessages } from "next-intl";

import { renderInline } from "@/lib/render-inline";

const COOKIE_CONSENT_KEY = "cookie_consent";

export function CookieBanner() {
  const t = useTranslations("cookieBanner");
  const messages = useMessages();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Only show if consent was never given
    if (localStorage.getItem(COOKIE_CONSENT_KEY) !== "true") {
      setVisible(true);
    }
  }, []);

  function handleAccept() {
    localStorage.setItem(COOKIE_CONSENT_KEY, "true");
    setVisible(false);
  }

  if (!visible) return null;

  // next-intl rejects custom XML tags like <link> in translation strings.
  // Access the raw message to let our renderInline handle the rich markup.
  const rawText: string = (messages as Record<string, Record<string, string>>)?.cookieBanner?.text ?? "";

  return (
    <div
      role="region"
      aria-label="Cookie banner"
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-line bg-white/95 px-4 py-4 shadow-lg backdrop-blur"
    >
      <div className="mx-auto flex max-w-5xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm leading-6 text-soft">
          {renderInline(rawText)}
        </p>
        <button
          type="button"
          onClick={handleAccept}
          className="inline-flex min-h-10 shrink-0 items-center justify-center rounded-pill bg-ink px-5 py-2 text-sm font-semibold text-white shadow-card transition hover:bg-ink/90"
        >
          {t("accept")}
        </button>
      </div>
    </div>
  );
}
