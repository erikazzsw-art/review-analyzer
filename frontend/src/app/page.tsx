import { useTranslations } from "next-intl";

import { BottomCta } from "@/components/marketing/bottom-cta";
import { HeroPreview } from "@/components/marketing/hero-preview";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { TrustSignal } from "@/components/marketing/trust-signal";
import { ValueGrid } from "@/components/marketing/value-grid";
import { Button } from "@/components/ui/button";
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
    <div className="page-bg-warm relative overflow-hidden">
      {/* V3 浮动 blob 装饰 */}
      <div className="blob-rose pointer-events-none absolute -top-32 -left-32 z-0" />
      <div className="blob-lavender pointer-events-none absolute top-32 -right-24 z-0" />

      <SiteHeader />

      {/* ===== Hero Section ===== */}
      <section className="relative z-10 mx-auto flex w-full max-w-7xl flex-col items-center gap-12 px-6 pb-16 pt-8 lg:flex-row lg:px-10 lg:pb-24 lg:pt-16">
        {/* Left side: text + CTAs */}
        <div className="flex flex-col items-center text-center lg:w-[55%] lg:items-start lg:text-left">
          {/* Eyebrow pill */}
          <div className="glass-rose mb-6 inline-flex rounded-pill px-4 py-1.5 text-[13px] font-medium text-[#f36f8f]">
            ✨ {t("heroEyebrow")}
          </div>

          {/* H1 - two lines */}
          <h1 className="font-heading text-[44px] font-extrabold leading-[1.05] tracking-[-0.02em] text-ink md:text-[60px]">
            {t("heroH1Line1")}
            <br />
            {t("heroH1Line2")}
          </h1>

          {/* Subtitle - 1 line */}
          <p className="mt-4 max-w-lg text-lg leading-relaxed text-soft md:text-xl">
            {t("heroSubtitleShort")}
          </p>

          {/* CTA buttons */}
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Button href="/register" variant="marketing" size="marketing">
              {t("heroCtaPrimary")}
            </Button>
            <Button href="/trial" variant="marketing-outline" size="marketing">
              {t("heroCtaSecondary")}
            </Button>
          </div>

          {/* Small text below buttons */}
          <p className="mt-4 text-[13px] text-soft">
            {t("heroNoCreditCard")}
          </p>
        </div>

        {/* Right side: HeroPreview + floating badges */}
        <div className="relative lg:w-[45%]">
          {/* Slight rotation for depth */}
          <div className="transition-transform duration-500 hover:rotate-0 lg:-rotate-1">
            <HeroPreview />
          </div>

          {/* Floating badge: top-right */}
          <div className="glass-rose pointer-events-none absolute -top-3 -right-3 inline-flex items-center gap-1.5 rounded-pill px-3 py-1.5 text-xs font-medium text-[#d94d72] shadow-sm md:-right-6">
            🔥 {t("heroBadgeImproved")}
          </div>

          {/* Floating badge: bottom-right */}
          <div className="glass-mint pointer-events-none absolute -bottom-3 -right-3 inline-flex items-center gap-1.5 rounded-pill px-3 py-1.5 text-xs font-medium text-[#2e9680] shadow-sm md:-right-6">
            ✓ {t("heroBadgeWeekly")}
          </div>
        </div>
      </section>

      {/* ===== How It Works ===== */}
      <HowItWorks />

      {/* ===== Trust / Social Proof ===== */}
      <section className="mx-auto w-full max-w-7xl px-6 pb-6 lg:px-10">
        <p className="text-center text-base text-soft">
          {t("trustStats")}
        </p>
      </section>
      <TrustSignal />

      {/* ===== Value Proposition Cards ===== */}
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 pb-20 lg:px-10">
        <ValueGrid />
      </div>

      {/* ===== Bottom CTA ===== */}
      <BottomCta />

      <SiteFooter />
    </div>
  );
}
