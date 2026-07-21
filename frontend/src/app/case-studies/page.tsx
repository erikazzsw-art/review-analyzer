import Link from "next/link";

import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { Button } from "@/components/ui/button";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "案例研究 — 跨境卖家如何用评论洞察改版产品",
  description:
    "真实案例展示：宠物出行包差评驱动改版评分从3.2升至4.5，手机壳发现尺寸适配问题退货率降45%。看看跨境卖家如何用 ReviewLens 评论分析提升产品力。",
  path: "/case-studies",
});

/* ------------------------------------------------------------------ */
/* 示意案例数据                                                        */
/* ------------------------------------------------------------------ */

interface CaseStudy {
  slug: string;
  title: string;
  beforeRating: string;
  afterRating: string;
  beforeTags: string[];
  afterTags: string[];
  metrics: { label: string; value: string }[];
  quote: string;
  colorAccent: string;
}

const CASE_STUDIES: CaseStudy[] = [
  {
    slug: "pet-travel-bag",
    title: "宠物出行包 — 差评驱动改版，评分从 3.2 升至 4.5",
    beforeRating: "3.2",
    afterRating: "4.5",
    beforeTags: ["拉链易卡顿", "尺寸偏小", "异味明显"],
    afterTags: ["拉链顺滑", "空间充裕", "无味材质"],
    metrics: [
      { label: "差评率", value: "↓62%" },
      { label: "复购率", value: "↑28%" },
    ],
    quote:
      "通过 ReviewLens 发现拉链是核心痛点，改版后差评大幅下降。",
    colorAccent: "#4fb99f",
  },
  {
    slug: "phone-case",
    title: "手机壳 — 发现尺寸适配问题，退货率降 45%",
    beforeRating: "3.5",
    afterRating: "4.6",
    beforeTags: ["尺寸不准", "开孔偏移", "手感粗糙"],
    afterTags: ["精准开孔", "完美贴合", "亲肤手感"],
    metrics: [
      { label: "退货率", value: "↓45%" },
      { label: "好评率", value: "↑35%" },
    ],
    quote:
      "ReviewLens 帮我们定位到 iPhone 15 Pro 开孔偏移是退货主因。",
    colorAccent: "#4fb99f",
  },
];

/* ------------------------------------------------------------------ */
/* 子组件                                                             */
/* ------------------------------------------------------------------ */

/** 上半部：Before/After 对比图 */
function ComparisonPanel({ study }: { study: CaseStudy }) {
  return (
    <div className="grid grid-cols-2 gap-3 overflow-hidden rounded-[16px]">
      {/* Before */}
      <div className="relative flex flex-col gap-2 rounded-[12px] bg-[#e8e4eb] p-4">
        <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#8a7f95]">
          改版前
        </span>
        {/* 示意产品区 */}
        <div className="flex h-24 items-center justify-center rounded-[10px] bg-[#d9d4de]">
          <svg
            className="h-10 w-10 text-[#b5adbd]"
            viewBox="0 0 48 48"
            fill="none"
          >
            <rect
              x="12"
              y="8"
              width="24"
              height="32"
              rx="4"
              stroke="currentColor"
              strokeWidth="2"
            />
            <circle cx="24" cy="22" r="5" stroke="currentColor" strokeWidth="2" />
            <path
              d="M16 36c0-4.4 3.6-8 8-8s8 3.6 8 8"
              stroke="currentColor"
              strokeWidth="2"
            />
          </svg>
        </div>
        {/* 评分 */}
        <div className="flex items-center gap-1.5">
          <span className="text-lg font-extrabold text-[#6f6877]">
            {study.beforeRating}
          </span>
          <Stars filled={3} color="#9b94a3" />
        </div>
        {/* 差评标签 */}
        <div className="flex flex-wrap gap-1">
          {study.beforeTags.map((t) => (
            <span
              key={t}
              className="rounded-[6px] bg-[#fce4e9] px-2 py-0.5 text-[11px] font-medium text-[#c94a5f]"
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* After */}
      <div className="relative flex flex-col gap-2 rounded-[12px] bg-[#e8f6f1] p-4">
        <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#3a9b80]">
          改版后
        </span>
        <div className="flex h-24 items-center justify-center rounded-[10px] bg-[#d2efe4]">
          <svg
            className="h-10 w-10 text-[#4fb99f]"
            viewBox="0 0 48 48"
            fill="none"
          >
            <rect
              x="12"
              y="8"
              width="24"
              height="32"
              rx="4"
              stroke="currentColor"
              strokeWidth="2"
            />
            <circle cx="24" cy="22" r="5" stroke="currentColor" strokeWidth="2" />
            <path
              d="M16 36c0-4.4 3.6-8 8-8s8 3.6 8 8"
              stroke="currentColor"
              strokeWidth="2"
            />
            <path
              d="M42 14l-18 18-6-6"
              stroke="#4fb99f"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-lg font-extrabold text-[#4fb99f]">
            {study.afterRating}
          </span>
          <Stars filled={5} color="#4fb99f" />
        </div>
        <div className="flex flex-wrap gap-1">
          {study.afterTags.map((t) => (
            <span
              key={t}
              className="rounded-[6px] bg-[#d4f5e9] px-2 py-0.5 text-[11px] font-medium text-[#2e9680]"
            >
              {t}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

/** 简易星级组件 */
function Stars({ filled, color }: { filled: number; color: string }) {
  return (
    <span className="inline-flex gap-0.5 text-xs" aria-hidden>
      {Array.from({ length: 5 }).map((_, i) => (
        <svg
          key={i}
          className="h-3 w-3"
          viewBox="0 0 24 24"
          fill={i < filled ? color : "none"}
          stroke={color}
          strokeWidth="1.5"
        >
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      ))}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* 主页面                                                             */
/* ------------------------------------------------------------------ */

export default function CaseStudiesPage() {
  return (
    <div className="page-bg-warm relative overflow-hidden">
      {/* V3 浮动 blob 装饰 */}
      <div className="blob-rose pointer-events-none absolute -top-32 -left-32 z-0" />
      <div className="blob-lavender pointer-events-none absolute top-20 -right-24 z-0" />

      <SiteHeader />

      <main className="relative z-10 mx-auto w-full max-w-7xl px-6 pb-20 pt-20 lg:px-10">
        {/* ===== Header ===== */}
        <header className="mb-14 text-center">
          <div className="mb-5 flex justify-center">
            <span className="glass-rose inline-flex rounded-pill px-4 py-1.5 text-[13px] font-medium uppercase tracking-[0.05em] text-[#f36f8f]">
              案例
            </span>
          </div>
          <h1 className="font-heading text-4xl font-extrabold leading-[1.12] tracking-[-0.02em] text-ink md:text-[44px]">
            跨境卖家如何用评论洞察改版产品
          </h1>
        </header>

        {/* ===== 2 列卡片网格 ===== */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* 示意案例卡片 */}
          {CASE_STUDIES.map((study) => (
            <article
              key={study.slug}
              className="glass-white flex flex-col gap-5 rounded-[24px] p-8 transition-all duration-300 hover:-translate-y-1 hover:shadow-glow"
            >
              {/* 上半：Before/After */}
              <ComparisonPanel study={study} />

              {/* 下半：信息区 */}
              <div className="flex flex-1 flex-col gap-3">
                {/* 标题 */}
                <h2 className="font-heading text-xl font-extrabold tracking-[-0.02em] text-ink">
                  {study.title}
                </h2>

                {/* 关键指标变化 */}
                <div className="flex flex-wrap gap-5">
                  {study.metrics.map((m) => (
                    <div key={m.label} className="flex items-baseline gap-1.5">
                      <span className="text-sm font-medium text-soft">
                        {m.label}
                      </span>
                      <span className="font-heading text-lg font-extrabold text-mint">
                        {m.value}
                      </span>
                    </div>
                  ))}
                </div>

                {/* 引用 */}
                <blockquote className="border-l-2 border-mint/30 pl-3 text-sm italic leading-relaxed text-soft">
                  &ldquo;{study.quote}&rdquo;
                </blockquote>

                {/* 阅读全文 link */}
                <div className="mt-auto pt-2">
                  <Link
                    href={`/case-studies/${study.slug}`}
                    className="inline-flex items-center gap-1 text-sm font-semibold text-rose transition-colors hover:text-[#d94d72]"
                  >
                    阅读全文
                    <svg
                      className="h-3.5 w-3.5"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M5 12h14" />
                      <path d="M12 5l7 7-7 7" />
                    </svg>
                  </Link>
                </div>
              </div>
            </article>
          ))}

          {/* CTA 卡片："成为我们的案例客户" */}
          <div className="glass-white flex flex-col items-center justify-center gap-5 rounded-[24px] border-2 border-dashed border-rose/30 p-8 text-center transition-all duration-300 hover:-translate-y-1">
            <div className="inline-flex h-14 w-14 items-center justify-center rounded-full bg-roseSoft">
              <svg
                className="h-6 w-6 text-rose"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 5v14" />
                <path d="M5 12h14" />
              </svg>
            </div>
            <h2 className="font-heading text-xl font-extrabold tracking-[-0.02em] text-ink">
              成为我们的案例客户
            </h2>
            <p className="max-w-xs text-sm leading-relaxed text-soft">
              分享你的产品改进故事，获得 ReviewLens 专属曝光与深度分析支持。
            </p>
            <Button
              href="mailto:hello@clueai.co"
              variant="marketing-outline"
              size="marketing"
            >
              分享你的案例
            </Button>
          </div>
        </div>

        {/* ===== 底部提示 ===== */}
        <p className="mt-14 text-center font-heading text-xl font-extrabold tracking-[-0.02em] text-ink">
          你的产品故事也可能在这里
        </p>
      </main>

      <SiteFooter />
    </div>
  );
}
