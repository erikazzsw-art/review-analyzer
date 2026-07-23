import { useTranslations } from "next-intl";

export function HeroPreview() {
  const t = useTranslations("marketing");

  return (
    <div className="overflow-hidden rounded-shell border border-line bg-white shadow-card">
      {/* Browser chrome */}
      <div className="flex items-center gap-2 border-b border-line bg-[#fafafa] px-4 py-2.5">
        <div className="flex gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
          <div className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
          <div className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        </div>
        <div className="ml-3 flex-1 rounded bg-[#f0f0f0] px-3 py-1 text-[10px] text-soft">
          app.clueai-reviewlens.com/analysis/results
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 p-4">
        {/* Top-left: Analysis metrics summary */}
        <div className="flex flex-col justify-between rounded-card border border-line bg-[#fafcff] p-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-soft">
            {t("heroInsight")}
          </span>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {[
              { label: t("heroMetricReviews"), value: "661", sub: "" },
              { label: t("heroMetricPositive"), value: "57.9%", sub: "" },
              { label: t("heroMetricNegative"), value: "42.1%", sub: "" },
              { label: t("heroMetricRating"), value: "3.5", sub: "/5" },
            ].map((m) => (
              <div key={m.label} className="rounded bg-white px-2.5 py-2 text-center shadow-sm">
                <div className="font-heading text-lg font-extrabold tracking-normal text-ink">
                  {m.value}
                  {m.sub && (
                    <span className="text-xs font-normal text-soft">{m.sub}</span>
                  )}
                </div>
                <div className="mt-0.5 text-[9px] text-soft">{m.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Top-right: Sentiment distribution */}
        <div className="flex flex-col justify-between rounded-card border border-line bg-[#fafcff] p-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-soft">
            {t("heroSentiment")}
          </span>
          <div className="mt-4 space-y-2">
            <div className="flex items-center gap-1">
              <div className="h-2 rounded-pill bg-[#f36f8f]/80" style={{ width: "15%" }} />
              <div className="h-2 rounded-pill bg-[#e8c94a]/60" style={{ width: "22%" }} />
              <div className="h-2 flex-1 rounded-pill bg-[#4fb99f]/70" />
            </div>
            <div className="flex justify-between text-[9px] text-soft">
              <span>{t("heroNegative")} 8%</span>
              <span>{t("heroNeutral")} 22%</span>
              <span>{t("heroPositive")} 70%</span>
            </div>
          </div>
          <div className="mt-2 text-right font-heading text-xl font-extrabold tracking-normal text-ink">
            1,284
            <span className="ml-1 text-[10px] font-normal text-soft">{t("heroReviews")}</span>
          </div>
        </div>

        {/* Bottom-left: Analysis dimensions (aspect tags) */}
        <div className="flex flex-col rounded-card border border-line bg-[#fafcff] p-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-soft">
            {t("heroAspects")}
          </span>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {[
              { label: t("heroAspectUsability"), pct: "82%" },
              { label: t("heroAspectValue"), pct: "37%" },
              { label: t("heroAspectDurability"), pct: "15%" },
              { label: t("heroAspectBuild"), pct: "13%" },
              { label: t("heroAspectPackaging"), pct: "4%" },
              { label: t("heroAspectFit"), pct: "4%" },
            ].map((item) => (
              <span
                key={item.label}
                className="inline-flex items-center gap-1 rounded-pill border border-line bg-white px-2 py-1 text-[9px] font-medium text-ink"
              >
                {item.label}
                <span className="text-soft">{item.pct}</span>
              </span>
            ))}
          </div>
        </div>

        {/* Bottom-right: Improvement trend */}
        <div className="flex flex-col rounded-card border border-line bg-[#fafcff] p-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-soft">
            {t("heroReview")}
          </span>
          <div className="mt-2 flex items-center gap-2">
            <span className="rounded-pill bg-roseSoft px-2 py-0.5 text-[9px] font-bold text-[#d94d72]">
              {t("heroNegativeRate")}
            </span>
            <span className="text-[9px] text-soft">{t("heroImprovement")}</span>
          </div>
          <svg
            className="mt-2 w-full flex-1"
            viewBox="0 0 120 44"
            fill="none"
            preserveAspectRatio="none"
          >
            <polyline
              points="0,12 20,14 40,10 55,16"
              stroke="#d94d72"
              strokeWidth="2"
              strokeLinecap="round"
              fill="none"
              opacity="0.6"
            />
            <polyline
              points="55,16 70,28 85,35 100,38 120,40"
              stroke="#4fb99f"
              strokeWidth="2"
              strokeLinecap="round"
              fill="none"
            />
            <line
              x1="55"
              y1="4"
              x2="55"
              y2="42"
              stroke="#e0e0e0"
              strokeWidth="0.8"
              strokeDasharray="2,2"
            />
            <text x="56" y="8" fontSize="5" fill="#999">
              {t("heroLaunched")}
            </text>
          </svg>
        </div>
      </div>
    </div>
  );
}
