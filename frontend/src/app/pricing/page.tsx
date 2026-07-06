import Link from "next/link";

import { MarketingShell } from "@/components/marketing/marketing-shell";
import { PricingFaq } from "@/components/marketing/pricing-faq";
import { ProCtaButton } from "@/components/marketing/pro-cta-button";
import { PLANS, type PlanPricing } from "@/lib/pricing";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "定价方案 | ClueAI ReviewLens",
  description:
    "对比 Free、Pro 和 Team 方案 — 评论智能分析、问评论、行动追踪，按需升级。人民币与美元双币标价。",
  path: "/pricing",
});

type PlanCard = {
  pricing: PlanPricing;
  highlight: boolean;
  cta: { label: string; href: string };
  features: string[];
};

const plans: PlanCard[] = [
  {
    pricing: PLANS.free,
    highlight: false,
    cta: { label: "免费开始", href: "/register" },
    features: [
      "1 个产品组",
      "单次最多 50 条评论分析",
      "基础情感分析 + 分类",
      "分析历史保留 7 天",
      "标准响应速度",
      "社区支持",
    ],
  },
  {
    pricing: PLANS.pro,
    highlight: true,
    cta: { label: "升级到 Pro", href: "/register?plan=pro" },
    features: [
      "不限产品组数量",
      "单次最多 500 条评论分析",
      "问评论 (RAG) 智能问答",
      "多版本 / 跨产品对比分析",
      "行动中心 + 复盘追踪",
      "AI 宣传文案生成",
      "分析历史永久保留",
      "优先响应 + 邮件支持",
    ],
  },
  {
    pricing: PLANS.team,
    highlight: false,
    cta: { label: "联系销售", href: "mailto:hello@clueai.co" },
    features: [
      "Pro 全部功能",
      "多成员协作 + 角色权限",
      "团队工作台 + 任务分派",
      "自定义分析模板",
      "API 接入 + Webhook 集成",
      "专属客户成功经理",
      "SLA 保障 + 优先排障",
    ],
  },
];

export default function PricingPage() {
  return (
    <div className="bg-hero-wash">
      <MarketingShell
        eyebrow="Pricing"
        title="简单透明的定价，随业务成长升级。"
        description="$19/月 · 约 ¥138 · Paddle 全球安全结算。免费开始体验核心分析能力，需要多产品管理、问评论、行动追踪时再升级 Pro。"
      />

      <div className="mx-auto grid w-full max-w-7xl gap-6 px-6 pb-16 lg:grid-cols-3 lg:px-10">
        {plans.map((plan) => (
          <article
            key={plan.pricing.key}
            className={[
              "relative flex flex-col rounded-shell border p-6 shadow-card",
              plan.highlight
                ? "border-2 border-[#d94d72] bg-white"
                : "border-line bg-white/86",
            ].join(" ")}
          >
            {plan.highlight && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-pill bg-[#d94d72] px-4 py-1 text-xs font-bold tracking-wider text-white">
                最受欢迎
              </div>
            )}
            <div className="text-sm font-semibold uppercase tracking-[0.12em] text-soft">
              {plan.pricing.name}
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="font-heading text-5xl font-extrabold tracking-[-0.04em] text-ink">
                {plan.pricing.priceUsd}
              </span>
              {plan.pricing.priceCnyApprox && (
                <span className="text-base font-semibold text-soft">
                  / 约 {plan.pricing.priceCnyApprox}
                </span>
              )}
              {plan.pricing.period && (
                <span className="text-base font-medium text-soft">
                  {plan.pricing.period}
                </span>
              )}
            </div>
            {plan.pricing.originalPriceUsd && (
              <div className="mt-1 text-xs text-soft">
                原价{" "}
                <span className="line-through">
                  {plan.pricing.originalPriceUsd}/月
                </span>
              </div>
            )}

            <div className="mt-6 flex-1 space-y-2.5">
              {plan.features.map((feature) => (
                <div
                  key={feature}
                  className="flex items-start gap-2 text-sm leading-6 text-ink"
                >
                  <svg
                    className="mt-0.5 h-4 w-4 shrink-0 text-[#4a7dc7]"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span>{feature}</span>
                </div>
              ))}
            </div>

            {plan.pricing.key === "pro" ? (
              <ProCtaButton
                label={plan.cta.label}
                className={[
                  "mt-8 inline-flex min-h-12 w-full items-center justify-center rounded-pill px-6 py-3 text-sm font-semibold shadow-card transition",
                  "bg-[#d94d72] text-white hover:bg-[#c4405f]",
                ].join(" ")}
              />
            ) : (
              <Link
                href={plan.cta.href}
                className={[
                  "mt-8 inline-flex min-h-12 w-full items-center justify-center rounded-pill px-6 py-3 text-sm font-semibold shadow-card transition",
                  plan.highlight
                    ? "bg-[#d94d72] text-white hover:bg-[#c4405f]"
                    : "border border-line bg-white text-ink hover:border-ink/20",
                ].join(" ")}
              >
                {plan.cta.label}
              </Link>
            )}
          </article>
        ))}
      </div>

      <PricingFaq />
    </div>
  );
}
