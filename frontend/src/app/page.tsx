import { useTranslations } from "next-intl";

import { HeroPreview } from "@/components/marketing/hero-preview";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { ValueGrid } from "@/components/marketing/value-grid";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "ReviewLens — 评论分析到产品行动的完整闭环",
  description:
    "支持多平台多格式评论上传，AI 自动分析输出 Top 问题与亮点，推送飞书到责任人，跟进改进落地，复盘优化效果。",
  path: "/",
});

export default function HomePage() {
  const t = useTranslations("marketing");

  return (
    <div className="bg-hero-wash">
      <MarketingShell
        eyebrow={t("eyebrow")}
        title={t("title")}
        subtitle={t("subtitle")}
        description={t("description")}
        aside={<HeroPreview />}
      />

      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 pb-20 lg:px-10">
        <ValueGrid />
      </div>
    </div>
  );
}
