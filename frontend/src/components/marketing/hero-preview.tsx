import { useTranslations } from "next-intl";

export function HeroPreview() {
  const t = useTranslations("marketing");

  return (
    <div className="grid h-full grid-cols-2 gap-3">
      {/* 评论洞察 — 简化柱状图 */}
      <div className="flex flex-col justify-between rounded-card border border-line bg-white/90 p-5">
        <span className="text-xs font-bold uppercase tracking-widest text-soft">{t("heroInsight")}</span>
        <div className="mt-3 flex items-end gap-1.5">
          {[68, 45, 82, 36, 58].map((h, i) => (
            <div key={i} className="flex flex-1 flex-col items-center gap-1">
              <div
                className="w-full rounded-sm bg-[linear-gradient(180deg,var(--rose),var(--lavender))]"
                style={{ height: `${h * 0.55}px` }}
              />
            </div>
          ))}
        </div>
        <div className="mt-2 flex justify-between text-[10px] text-soft">
          <span>{t("heroCatPackaging")}</span>
          <span>{t("heroCatLogistics")}</span>
          <span>{t("heroCatQuality")}</span>
          <span>{t("heroCatFunction")}</span>
          <span>{t("heroCatDescription")}</span>
        </div>
      </div>

      {/* 情感分布 — 三色进度条 */}
      <div className="flex flex-col justify-between rounded-card border border-line bg-white/90 p-5">
        <span className="text-xs font-bold uppercase tracking-widest text-soft">{t("heroSentiment")}</span>
        <div className="mt-4 space-y-2">
          <div className="flex items-center gap-2">
            <div className="h-2 flex-1 rounded-pill bg-[#f36f8f]/80" style={{ width: "15%" }} />
            <div className="h-2 flex-[2] rounded-pill bg-[#e8c94a]/60" />
            <div className="h-2 flex-[7] rounded-pill bg-[#4fb99f]/70" />
          </div>
          <div className="flex justify-between text-[10px] text-soft">
            <span>{t("heroNegative")} 8%</span>
            <span>{t("heroNeutral")} 22%</span>
            <span>{t("heroPositive")} 70%</span>
          </div>
        </div>
        <div className="mt-3 text-right font-heading text-2xl font-extrabold tracking-tight text-ink">
          1,284
          <span className="ml-1 text-xs font-normal text-soft">{t("heroReviews")}</span>
        </div>
      </div>

      {/* 措施跟进 — 进度条 */}
      <div className="flex flex-col rounded-card border border-line bg-white/90 p-5">
        <span className="text-xs font-bold uppercase tracking-widest text-soft">{t("heroActions")}</span>
        <div className="mt-4 space-y-3">
          {[
            { label: t("heroActionPackaging"), pct: 85, color: "var(--mint)" },
            { label: t("heroActionManual"), pct: 60, color: "var(--lavender)" },
            { label: t("heroActionSize"), pct: 35, color: "var(--rose)" },
          ].map((item) => (
            <div key={item.label}>
              <div className="flex justify-between text-[11px]">
                <span className="text-ink">{item.label}</span>
                <span className="font-semibold text-soft">{item.pct}%</span>
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-pill bg-line">
                <div
                  className="h-full rounded-pill transition-all"
                  style={{ width: `${item.pct}%`, background: item.color }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 复盘验证 — 简化折线趋势 */}
      <div className="flex flex-col rounded-card border border-line bg-white/90 p-5">
        <span className="text-xs font-bold uppercase tracking-widest text-soft">{t("heroReview")}</span>
        <div className="mt-2 flex items-center gap-2">
          <span className="rounded-pill bg-roseSoft px-2 py-0.5 text-[10px] font-bold text-[#d94d72]">{t("heroNegativeRate")}</span>
          <span className="text-[10px] text-soft">{t("heroImprovement")}</span>
        </div>
        <svg className="mt-3 w-full flex-1" viewBox="0 0 120 48" fill="none" preserveAspectRatio="none">
          <polyline
            points="0,12 20,14 40,10 55,16"
            stroke="var(--rose)"
            strokeWidth="2"
            strokeLinecap="round"
            fill="none"
            opacity="0.6"
          />
          <polyline
            points="55,16 70,28 85,35 100,38 120,40"
            stroke="var(--mint)"
            strokeWidth="2"
            strokeLinecap="round"
            fill="none"
          />
          <line x1="55" y1="4" x2="55" y2="46" stroke="var(--line)" strokeWidth="0.8" strokeDasharray="2,2" />
          <text x="56" y="8" fontSize="5" fill="var(--soft)">{t("heroLaunched")}</text>
        </svg>
      </div>
    </div>
  );
}
