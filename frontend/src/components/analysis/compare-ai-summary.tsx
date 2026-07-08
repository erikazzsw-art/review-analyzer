"use client";

import { useTranslations } from "next-intl";

import type { CompareAiSummary } from "@/lib/api/types";

type CompareAiSummaryProps = {
  summary: CompareAiSummary | null | undefined;
};

export function CompareAiSummary({ summary }: CompareAiSummaryProps) {
  const t = useTranslations("analysis.compare");
  if (!summary) {
    return (
      <section className="rounded-shell border border-dashed border-line bg-[#fffafb] px-5 py-6 text-sm text-soft">
        {t("aiSummaryEmpty")}
      </section>
    );
  }

  const hasBody =
    Boolean(summary.headline) ||
    summary.summary.length > 0 ||
    summary.recommendations.length > 0 ||
    summary.risks.length > 0;

  if (!hasBody) {
    return null;
  }

  return (
    <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
      <div className="inline-flex rounded-pill bg-[#eef6ff] px-3 py-1 text-[10px] font-bold tracking-[0.12em] text-[#4a7dc7]">
        {t("aiSummaryBadge")}
      </div>
      {summary.headline ? (
        <h3 className="mt-2 font-heading text-lg font-extrabold tracking-[-0.04em] text-ink">
          {summary.headline}
        </h3>
      ) : null}
      {summary.summary.length > 0 ? (
        <div className="mt-3 space-y-1 text-sm leading-6 text-ink">
          {summary.summary.map((item, index) => (
            <p key={`summary-${index}`}>· {item}</p>
          ))}
        </div>
      ) : null}
      {summary.recommendations.length > 0 || summary.risks.length > 0 ? (
        <div className="mt-4 grid gap-3 xl:grid-cols-2">
          {summary.recommendations.length > 0 ? (
            <div className="rounded-card border border-line bg-[#f8fffc] px-4 py-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-soft">
                {t("recommendActions")}
              </div>
              <div className="mt-2 space-y-1 text-sm leading-6 text-ink">
                {summary.recommendations.map((item, index) => (
                  <p key={`rec-${index}`}>· {item}</p>
                ))}
              </div>
            </div>
          ) : null}
          {summary.risks.length > 0 ? (
            <div className="rounded-card border border-line bg-[#fff8f9] px-4 py-3">
              <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-soft">
                {t("riskWarning")}
              </div>
              <div className="mt-2 space-y-1 text-sm leading-6 text-ink">
                {summary.risks.map((item, index) => (
                  <p key={`risk-${index}`}>⚠ {item}</p>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
