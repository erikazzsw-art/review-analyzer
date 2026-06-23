import { useTranslations } from "next-intl";

export function HeroPreview() {
  const t = useTranslations("marketing");

  return (
    <div className="overflow-hidden rounded-shell border border-line bg-white shadow-card">
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
        <div className="flex flex-col justify-between rounded-card border border-line bg-[#fafcff] p-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-soft">{t("heroInsight")}</span>
          <div className="mt-3 flex items-end gap-1.5">
            {[68, 45, 82, 36, 58].map((h, i) => (
              <div key={i} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="w-full rounded-sm bg-[linear-gradient(180deg,#d94d72,#8b7ec8)]"
                  style={{ height: `${h * 0.5}px` }}
                />
              </div>
            ))}
          </div>
          <div className="mt-2 flex justify-between text-[9px] text-soft">
            <span>{t("heroCatPackaging")}</span>
            <span>{t("heroCatLogistics")}</span>
            <span>{t("heroCatQuality")}</span>
            <span>{t("heroCatFunction")}</span>
            <span>{t("heroCatDescription")}</span>
          </div>
        </div>

        <div className="flex flex-col justify-between rounded-card border border-line bg-[#fafcff] p-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-soft">{t("heroSentiment")}</span>
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
          <div className="mt-2 text-right font-heading text-xl font-extrabold tracking-tight text-ink">
            1,284
            <span className="ml-1 text-[10px] font-normal text-soft">{t("heroReviews")}</span>
          </div>
        </div>

        <div className="flex flex-col rounded-card border border-line bg-[#fafcff] p-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-soft">{t("heroActions")}</span>
          <div className="mt-3 space-y-2.5">
            {[
              { label: t("heroActionPackaging"), pct: 85, color: "#4fb99f" },
              { label: t("heroActionManual"), pct: 60, color: "#8b7ec8" },
              { label: t("heroActionSize"), pct: 35, color: "#d94d72" },
            ].map((item) => (
              <div key={item.label}>
                <div className="flex justify-between text-[10px]">
                  <span className="text-ink">{item.label}</span>
                  <span className="font-semibold text-soft">{item.pct}%</span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-pill bg-[#f0f0f0]">
                  <div
                    className="h-full rounded-pill"
                    style={{ width: `${item.pct}%`, background: item.color }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col rounded-card border border-line bg-[#fafcff] p-4">
          <span className="text-[10px] font-bold uppercase tracking-widest text-soft">{t("heroReview")}</span>
          <div className="mt-2 flex items-center gap-2">
            <span className="rounded-pill bg-roseSoft px-2 py-0.5 text-[9px] font-bold text-[#d94d72]">{t("heroNegativeRate")}</span>
            <span className="text-[9px] text-soft">{t("heroImprovement")}</span>
          </div>
          <svg className="mt-2 w-full flex-1" viewBox="0 0 120 44" fill="none" preserveAspectRatio="none">
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
            <line x1="55" y1="4" x2="55" y2="42" stroke="#e0e0e0" strokeWidth="0.8" strokeDasharray="2,2" />
            <text x="56" y="8" fontSize="5" fill="#999">{t("heroLaunched")}</text>
          </svg>
        </div>
      </div>
    </div>
  );
}
