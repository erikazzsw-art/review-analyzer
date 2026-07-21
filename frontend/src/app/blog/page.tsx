import Link from "next/link";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "博客 — 跨境电商评论分析洞察",
  description:
    "ReviewLens 博客 — 从差评中提取产品改进信号、掌握评论分析关键指标、了解 AI 驱动产品改版的最佳实践。每周一篇分析干货。",
  path: "/blog",
});

/* ── 种子文章数据 ── */
const SEED_ARTICLES = [
  {
    slug: "extract-improvement-signals-from-negative-reviews",
    title: "如何从差评中提取产品改进信号",
    date: "2026-07-15",
    readTime: "5 min read",
    tags: ["评论分析", "跨境电商", "产品改进"],
    gradient: "from-[#f36f8f] to-[#8d7be8]",
  },
  {
    slug: "5-key-metrics-for-cross-border-review-analysis",
    title: "跨境电商评论分析的 5 个关键指标",
    date: "2026-07-08",
    readTime: "4 min read",
    tags: ["评论分析", "数据指标", "跨境电商"],
    gradient: "from-[#4fb99f] to-[#38b2ac]",
  },
  {
    slug: "ai-driven-product-iteration-closed-loop",
    title: "AI 驱动产品改版：从数据到行动的闭环",
    date: "2026-07-01",
    readTime: "6 min read",
    tags: ["AI 分析", "产品改版", "案例"],
    gradient: "from-[#e5a63b] to-[#f97316]",
  },
];

/* ── 标签云 ── */
const TAG_CLOUD = [
  { label: "评论分析", count: 12 },
  { label: "跨境电商", count: 9 },
  { label: "AI 分析", count: 8 },
  { label: "产品改进", count: 6 },
  { label: "数据指标", count: 5 },
  { label: "案例", count: 4 },
  { label: "NLP", count: 3 },
  { label: "客户体验", count: 3 },
];

/* ── 分页 ── */
const PAGINATION = {
  current: 1,
  total: 1,
};

export default function BlogPage() {
  return (
    <div className="relative min-h-screen page-bg-warm overflow-hidden">
      {/* V3 浮动 blob 装饰 */}
      <div className="blob-rose absolute -top-32 -left-32 z-0" />
      <div className="blob-lavender absolute top-20 -right-24 z-0" />

      <SiteHeader />

      <main className="relative z-10 mx-auto w-full max-w-7xl px-6 pb-16 pt-4 lg:px-10">
        {/* ── Header ── */}
        <section className="mb-8 text-center">
          <div className="mb-4 inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold uppercase tracking-[0.12em] text-[#d94d72]">
            博客
          </div>
          <h1 className="font-heading text-4xl font-extrabold leading-[1.02] tracking-[-0.04em] text-ink md:text-5xl">
            跨境电商评论分析洞察
          </h1>
        </section>

        {/* ── 主内容区：卡片网格 + 侧边栏 ── */}
        <div className="flex flex-col gap-10 lg:flex-row">
          {/* 左侧：博客卡片网格（3 列） */}
          <div className="flex-1">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {SEED_ARTICLES.map((article) => (
                <Link
                  key={article.slug}
                  href={`/blog/${article.slug}`}
                  className="glass-white group flex flex-col overflow-hidden transition-all duration-300 ease-out hover:scale-[1.02] hover:shadow-glow"
                >
                  {/* 上部 60%：渐变占位图 */}
                  <div
                    className={`relative aspect-[16/10] bg-gradient-to-br ${article.gradient} flex items-center justify-center`}
                  >
                    {/* 装饰性几何图形 */}
                    <div className="absolute inset-0 opacity-10">
                      <div className="absolute right-4 top-4 h-12 w-12 rounded-full border-2 border-white" />
                      <div className="absolute bottom-4 left-4 h-16 w-16 rounded-lg border-2 border-white" />
                      <div className="absolute right-12 bottom-8 h-8 w-8 rotate-45 border-2 border-white" />
                    </div>
                    <span className="relative z-10 text-sm font-medium uppercase tracking-[0.1em] text-white/50">
                      封面图片
                    </span>
                  </div>

                  {/* 下部 40%：内容区 */}
                  <div className="flex flex-1 flex-col gap-3 p-5">
                    {/* 分类标签 pill */}
                    <div className="flex flex-wrap gap-2">
                      {article.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex rounded-pill bg-roseSoft px-2.5 py-0.5 text-[11px] font-medium text-[#d94d72]"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>

                    {/* 标题（18px，2 行截断） */}
                    <h2 className="line-clamp-2 text-[18px] font-semibold leading-snug text-ink group-hover:text-rose transition-colors duration-200">
                      {article.title}
                    </h2>

                    {/* 日期 + 阅读时间 */}
                    <div className="mt-auto flex items-center gap-3 text-[13px] text-soft">
                      <span>{article.date}</span>
                      <span className="text-line">·</span>
                      <span>{article.readTime}</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>

            {/* ── 底部分页 ── */}
            <div className="mt-10 flex items-center justify-center gap-2">
              {/* 上一页（disabled） */}
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-pill text-sm text-soft/40 cursor-not-allowed select-none">
                ←
              </span>

              {/* 当前页 */}
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-pill bg-rose text-sm font-semibold text-white">
                {PAGINATION.current}
              </span>

              {/* 下一页（disabled） */}
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-pill text-sm text-soft/40 cursor-not-allowed select-none">
                →
              </span>
            </div>
          </div>

          {/* 右侧边栏（桌面端） */}
          <aside className="w-full shrink-0 lg:w-[280px]">
            <div className="flex flex-col gap-6 lg:sticky lg:top-24">
              {/* 热门标签 */}
              <div className="glass-white p-5">
                <h3 className="mb-3 font-heading text-sm font-bold uppercase tracking-[0.06em] text-ink">
                  热门标签
                </h3>
                <div className="flex flex-wrap gap-2">
                  {TAG_CLOUD.map((tag) => (
                    <span
                      key={tag.label}
                      className="inline-flex cursor-pointer items-center gap-1 rounded-pill border border-line bg-white/50 px-3 py-1 text-xs text-soft transition-colors duration-200 hover:border-rose hover:text-rose"
                    >
                      {tag.label}
                      <span className="text-[10px] text-soft/60">
                        ({tag.count})
                      </span>
                    </span>
                  ))}
                </div>
              </div>

              {/* 订阅 CTA */}
              <div className="glass-rose p-5 text-center">
                <h3 className="mb-1 font-heading text-sm font-bold uppercase tracking-[0.06em] text-[#d94d72]">
                  订阅更新
                </h3>
                <p className="mb-4 text-[13px] leading-relaxed text-soft">
                  每周一篇分析干货，不错过任何洞察
                </p>
                <form
                  className="flex flex-col gap-2"
                  onSubmit={(e) => e.preventDefault()}
                >
                  <input
                    type="email"
                    placeholder="your@email.com"
                    className="w-full rounded-pill border border-line bg-white/70 px-4 py-2 text-[13px] text-ink placeholder:text-soft/50 outline-none transition-colors duration-200 focus:border-rose focus:bg-white"
                  />
                  <button
                    type="submit"
                    className="w-full rounded-pill bg-rose px-4 py-2 text-[13px] font-semibold text-white transition-all duration-200 hover:brightness-110 active:scale-[0.98]"
                  >
                    订阅
                  </button>
                </form>
              </div>
            </div>
          </aside>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
