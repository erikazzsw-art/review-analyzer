"use client";

import { useTranslations } from "next-intl";

import { MarketingShell } from "@/components/marketing/marketing-shell";

type Channel = "privacy" | "support" | "hello";

const CHANNELS: readonly Channel[] = ["privacy", "support", "hello"] as const;

export default function ContactPage() {
  const t = useTranslations("contact");

  return (
    <MarketingShell title={t("title")} description={t("description")}>
      <div className="mx-auto max-w-4xl px-4 py-6">
        <div className="grid gap-4 md:grid-cols-3">
          {CHANNELS.map((channel) => {
            const email = t(`${channel}.email`);
            return (
              <div
                key={channel}
                className="flex flex-col gap-3 rounded-xl border border-line bg-white/60 p-6 shadow-card backdrop-blur"
              >
                <span className="inline-flex w-fit rounded-pill bg-roseSoft px-3 py-1 text-[11px] font-bold uppercase tracking-[0.1em] text-[#d94d72]">
                  {t(`${channel}.label`)}
                </span>
                <a
                  href={`mailto:${email}`}
                  className="break-all font-heading text-base font-semibold text-ink underline decoration-dotted underline-offset-4 hover:opacity-80"
                >
                  {email}
                </a>
                <p className="text-sm leading-6 text-soft">
                  {t(`${channel}.description`)}
                </p>
              </div>
            );
          })}
        </div>
        <p className="mt-8 text-center text-xs text-muted-foreground">
          {t("responseTime")}
        </p>
      </div>
    </MarketingShell>
  );
}
