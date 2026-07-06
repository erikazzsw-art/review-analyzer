"use client";

import { useTranslations } from "next-intl";

import { MarketingShell } from "@/components/marketing/marketing-shell";

type SubProcessor = {
  name: string;
  purpose: string;
  region: string;
  dpa: string;
};

const SUB_PROCESSORS: readonly SubProcessor[] = [
  {
    name: "Supabase",
    purpose: "Managed PostgreSQL database & authentication",
    region: "AWS ap-southeast-1 / us-east-1",
    dpa: "https://supabase.com/privacy",
  },
  {
    name: "Cloudflare",
    purpose: "CDN, WAF, DDoS protection",
    region: "Global edge network",
    dpa: "https://www.cloudflare.com/privacypolicy/",
  },
  {
    name: "Anthropic",
    purpose: "LLM inference (review analysis)",
    region: "United States",
    dpa: "https://www.anthropic.com/legal/privacy",
  },
  {
    name: "DataForSEO",
    purpose: "Amazon review data collection",
    region: "United States",
    dpa: "https://dataforseo.com/privacy-policy",
  },
  {
    name: "Rainforest API",
    purpose: "Amazon review data (fallback)",
    region: "United States",
    dpa: "https://www.rainforestapi.com/privacy",
  },
  {
    name: "Paddle",
    purpose: "Payment processing & merchant of record",
    region: "European Union / Global",
    dpa: "https://www.paddle.com/legal/gdpr",
  },
  {
    name: "Resend",
    purpose: "Transactional & marketing email delivery",
    region: "United States",
    dpa: "https://resend.com/legal/privacy-policy",
  },
  {
    name: "Cloudflare Web Analytics",
    purpose: "Privacy-friendly website analytics",
    region: "Global edge network",
    dpa: "https://www.cloudflare.com/web-analytics-privacy/",
  },
] as const;

export default function SubProcessorsPage() {
  const t = useTranslations("subProcessors");

  return (
    <MarketingShell title={t("title")} description={t("description")}>
      <div className="mx-auto max-w-5xl px-4 py-6">
        <p className="mb-4 text-xs text-muted-foreground">{t("lastUpdated")}</p>

        {/* Desktop table */}
        <div className="hidden overflow-hidden rounded-xl border border-line bg-white/60 shadow-card backdrop-blur md:block">
          <table className="w-full text-sm">
            <thead className="bg-hero-wash">
              <tr className="border-b border-line text-left font-heading text-xs uppercase tracking-[0.08em] text-soft">
                <th className="px-5 py-3 font-semibold">{t("provider")}</th>
                <th className="px-5 py-3 font-semibold">{t("purpose")}</th>
                <th className="px-5 py-3 font-semibold">{t("region")}</th>
                <th className="px-5 py-3 font-semibold">{t("dpa")}</th>
              </tr>
            </thead>
            <tbody>
              {SUB_PROCESSORS.map((sp, index) => (
                <tr
                  key={sp.name}
                  className={
                    index !== SUB_PROCESSORS.length - 1
                      ? "border-b border-line/60"
                      : ""
                  }
                >
                  <td className="px-5 py-4 font-semibold text-ink">
                    {sp.name}
                  </td>
                  <td className="px-5 py-4 text-soft">{sp.purpose}</td>
                  <td className="px-5 py-4 text-soft">{sp.region}</td>
                  <td className="px-5 py-4">
                    <a
                      href={sp.dpa}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs font-semibold text-ink underline decoration-dotted underline-offset-4 hover:opacity-80"
                    >
                      {t("learnMore")}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile cards */}
        <div className="grid gap-3 md:hidden">
          {SUB_PROCESSORS.map((sp) => (
            <div
              key={sp.name}
              className="rounded-xl border border-line bg-white/60 p-4 shadow-card backdrop-blur"
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-heading text-base font-bold text-ink">
                  {sp.name}
                </h3>
                <a
                  href={sp.dpa}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-semibold text-ink underline decoration-dotted underline-offset-4"
                >
                  {t("learnMore")}
                </a>
              </div>
              <dl className="mt-3 space-y-1.5 text-xs">
                <div className="flex gap-2">
                  <dt className="min-w-16 text-muted-foreground">
                    {t("purpose")}
                  </dt>
                  <dd className="text-soft">{sp.purpose}</dd>
                </div>
                <div className="flex gap-2">
                  <dt className="min-w-16 text-muted-foreground">
                    {t("region")}
                  </dt>
                  <dd className="text-soft">{sp.region}</dd>
                </div>
              </dl>
            </div>
          ))}
        </div>

        <p className="mt-6 text-xs text-muted-foreground">{t("quarterly")}</p>
      </div>
    </MarketingShell>
  );
}
