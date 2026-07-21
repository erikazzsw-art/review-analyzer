import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/marketing/site-header";
import { SiteFooter } from "@/components/marketing/site-footer";
import { BottomCta } from "@/components/marketing/bottom-cta";
import { buildMarketingMetadata } from "@/lib/seo";
import { BlogToc } from "./toc";

/* ================================================================
   种子文章数据
   ================================================================ */

interface ArticleSection {
  type: "h2" | "paragraph" | "blockquote" | "image";
  id?: string;
  text?: string;
  caption?: string;
  gradient?: string;
}

interface SeedArticle {
  slug: string;
  title: string;
  date: string;
  author: string;
  readTime: string;
  tags: string[];
  gradient: string;
  excerpt: string;
  sections: ArticleSection[];
}

const ARTICLES: Record<string, SeedArticle> = {
  "extract-improvement-signals-from-negative-reviews": {
    slug: "extract-improvement-signals-from-negative-reviews",
    title: "如何从差评中提取产品改进信号",
    date: "2026-07-15",
    author: "ReviewLens 团队",
    readTime: "5 min read",
    tags: ["评论分析", "跨境电商", "产品改进"],
    gradient: "from-[#f36f8f] to-[#8d7be8]",
    excerpt:
      "差评不是终点，而是产品迭代的起点。本文分享一套系统化的差评分析方法，帮助跨境电商卖家从负面反馈中提炼可执行的产品改进清单。",
    sections: [
      {
        type: "paragraph",
        text: "在跨境电商领域，差评往往是卖家最头疼的问题。一条一星差评可能让转化率下跌 15%，而十条差评足以毁掉一款新品。但换个角度看，每一条差评都包含了用户最真实的使用体验和改进诉求——这些信息如果通过传统市场调研获取，成本可能高达数千美元。",
      },
      {
        type: "paragraph",
        text: "据 Jungle Scout 2025 年报告，超过 72% 的亚马逊买家在购买前会阅读评论，而其中 68% 会专门查看差评。这意味着差评不仅影响你的转化，更影响着潜在客户对产品的第一印象。但如果处理得当，差评反而能成为你超越竞争对手的武器。",
      },
      {
        type: "h2",
        id: "why-negative-reviews-matter",
        text: "差评是金矿：为什么负面反馈更有价值",
      },
      {
        type: "paragraph",
        text: "正面评价虽然令人愉悦，但往往缺乏具体信息——'很好用'、'不错'这类评论无法指导产品迭代。而差评恰恰相反：用户因为遇到了真实的问题，所以更愿意详细描述使用场景、期望和落差。一条典型的差评通常包含三个关键信息：使用场景（什么时候用、怎么用）、问题描述（具体出了什么问题）、期望落差（用户觉得应该怎样但实际上怎样）。",
      },
      {
        type: "paragraph",
        text: "对于跨境电商卖家来说，差评还额外携带了地域信息。比如一款手机支架，美国用户抱怨'夹不住大尺寸手机'，欧洲用户投诉'出风口挂钩不兼容'，日本用户吐槽'太占地方'。这些差异化的反馈揭示了不同市场的需求差异，是全球化产品迭代的重要参考。",
      },
      {
        type: "blockquote",
        text: "好的产品经理不是看用户说了什么，而是从用户抱怨中看到产品缺失的功能。差评是最便宜的产品需求文档。",
      },
      {
        type: "h2",
        id: "four-step-extraction",
        text: "四步提取法：从差评到产品改进清单",
      },
      {
        type: "paragraph",
        text: "第一步：批量采集与分类。使用 ReviewLens 等工具将差评（1-2 星）按主题自动归类——尺寸问题、材质问题、功能缺陷、包装破损、描述不符等。AI 聚类可以在一分钟内完成人工需要数小时的分类工作。",
      },
      {
        type: "paragraph",
        text: "第二步：频次排序。不是所有差评都值得立刻响应。将问题按出现频次排序，重点关注 Top 5 高频问题。根据我们的经验，解决排名前三的问题通常能消除 60% 以上的差评来源。",
      },
      {
        type: "paragraph",
        text: "第三步：根因分析。每个高频问题背后都有一条因果链。例如'容易掉'不只是胶水问题——可能是材质太光滑、表面有油污、胶水配方不兼容、运输过程高温导致胶水失效等。AI 辅助分析可以帮你快速定位最可能的根因。",
      },
      {
        type: "paragraph",
        text: "第四步：生成改进清单。将根因转化为可执行的具体行动：'改用 3M VHB 双面胶'比'改进粘性'更有操作性；'增加硅胶防滑垫'比'优化设计'更容易落地。每条改进措施都需要标注优先级（P0/P1/P2）、预计成本、预期效果。",
      },
      {
        type: "image",
        gradient: "from-[#f36f8f] to-[#8d7be8]",
        caption: "图：四步差评分析法工作流程",
      },
      {
        type: "h2",
        id: "real-case-study",
        text: "真实案例：一个 3C 配件卖家的改版之路",
      },
      {
        type: "paragraph",
        text: "某 3C 配件卖家（年销 $2M）的手机壳产品线面临评分持续下滑的困境——从 4.3 星降到 3.8 星仅用了两个月。通过系统化分析 247 条差评，团队发现前三大问题依次为：按键手感偏硬（37%）、颜色与图片存在色差（28%）、MagSafe 磁吸力不足（18%）。",
      },
      {
        type: "paragraph",
        text: "团队按优先级逐一解决：与工厂调整按键硅胶硬度配方，引入色卡标准化流程，升级磁铁规格。改版后重新上架，三个月内评分回升至 4.5 星，月销量增长 40%。更关键的是，他们建立了一套'评论驱动的持续改进机制'——每周自动采集新评论，AI 归类后生成改进建议，产品经理在周会上评估并排入迭代计划。",
      },
      {
        type: "paragraph",
        text: "这个案例验证了一个核心逻辑：差评分析不是一次性项目，而应该是一个持续运转的反馈系统。越早建立这套系统，你的产品迭代速度就越快于竞争对手。",
      },
    ],
  },

  "5-key-metrics-for-cross-border-review-analysis": {
    slug: "5-key-metrics-for-cross-border-review-analysis",
    title: "跨境电商评论分析的 5 个关键指标",
    date: "2026-07-08",
    author: "ReviewLens 数据团队",
    readTime: "4 min read",
    tags: ["评论分析", "数据指标", "跨境电商"],
    gradient: "from-[#4fb99f] to-[#38b2ac]",
    excerpt:
      "告别凭感觉做决策。掌握情感得分、问题聚类、趋势变化、竞品对比、行动转化率这 5 个核心指标，让数据驱动你的产品迭代决策。",
    sections: [
      {
        type: "paragraph",
        text: "很多跨境电商卖家做评论分析时，习惯'扫一眼评分和最近几条差评'，然后凭感觉判断产品哪里需要改进。这种方式的致命缺陷在于：人的注意力天然倾向于最新的、情绪最激烈的评论，而忽略了更重要的统计规律。",
      },
      {
        type: "paragraph",
        text: "要真正从评论数据中提取可靠的产品洞察，你需要一套标准化的指标体系。以下是我们在服务 500+ 跨境卖家中提炼出的 5 个核心指标，每一个都直接对应一项可执行的产品或运营决策。",
      },
      {
        type: "h2",
        id: "metric-sentiment",
        text: "指标一：情感极性得分",
      },
      {
        type: "paragraph",
        text: "情感极性得分不是简单的平均星数。ReviewLens 使用 NLP 模型对评论文本做细粒度情感分析，每条评论输出 0-100 的情感分（0=极度负面，100=极度正面）。相比星数，情感分的优势在于：用户可能打了 4 星但文字充满抱怨（'还行，但是...'），也可能打了 3 星但文字积极（'有点小问题，但整体不错'）。",
      },
      {
        type: "paragraph",
        text: "更重要的是，情感得分可以按维度拆解。一款产品可能整体情感分不错，但'包装'维度持续低迷——这提示你需要优化包装方案，而不是产品本身。每周追踪分维度情感得分，可以帮助你精准定位问题的出现时间点和具体维度。",
      },
      {
        type: "h2",
        id: "metric-clustering",
        text: "指标二：高频问题聚类",
      },
      {
        type: "paragraph",
        text: "单个差评可能是偶然，但 30 条差评同时提到'按键手感偏硬'就一定是问题。高频问题聚类通过 NLP 技术自动将语义相似的评论归为一组，输出每个问题簇的提及次数、占比、趋势。",
      },
      {
        type: "paragraph",
        text: "我们建议每周关注 Top 5 问题簇的变化：有没有新问题出现？老问题的提及频率在上升还是下降？上升意味着问题在恶化（可能是新批次品控出问题），下降则意味着之前的改进措施正在生效。",
      },
      {
        type: "blockquote",
        text: "数据本身不创造价值，对数据的持续追踪和响应才创造价值。设置周度评论回顾机制，让数据流动起来。",
      },
      {
        type: "h2",
        id: "metrics-three-to-five",
        text: "指标三到五：趋势变化、竞品对比、行动转化率",
      },
      {
        type: "paragraph",
        text: "指标三：趋势变化率。问题不会一夜之间出现。通过对比近 7 天 vs 近 30 天 vs 近 90 天的评论数据，你可以捕捉到问题的早期信号。比如'掉色'的提及量在过去一周突然翻了 3 倍，这可能意味着最近批次的染色工艺出了问题。设置趋势告警阈值，当某个问题簇的提及频率在 7 天内上升超过 50% 时自动通知，可以在差评爆发前及时干预。",
      },
      {
        type: "paragraph",
        text: "指标四：竞品评论对比。你的差评中 30% 提到'磁吸力不足'，而竞品 A 只有 5%——这说明磁吸设计确实是你的短板。但如果所有竞品的差评中都有 25%+ 提到磁吸力，那说明这是行业通病，可能受限于当前技术/成本。竞品评论分析帮你区分'你的问题'和'品类的问题'，避免在不值得的地方投入过多资源。",
      },
      {
        type: "paragraph",
        text: "指标五：改进行动转化率。这是最常被忽视但最重要的指标。你从评论中提炼了 10 条改进建议，实际落地了几条？落地后对应问题簇的提及频率有没有下降？如果没有，是方案不对还是执行不到位？建立一个'评论洞察→改进行动→效果验证'的闭环追踪表，让数据真正驱动产品迭代。",
      },
      {
        type: "image",
        gradient: "from-[#4fb99f] to-[#38b2ac]",
        caption: "图：5 个核心指标监控仪表盘示意",
      },
    ],
  },

  "ai-driven-product-iteration-closed-loop": {
    slug: "ai-driven-product-iteration-closed-loop",
    title: "AI 驱动产品改版：从数据到行动的闭环",
    date: "2026-07-01",
    author: "ReviewLens 产品团队",
    readTime: "6 min read",
    tags: ["AI 分析", "产品改版", "案例"],
    gradient: "from-[#e5a63b] to-[#f97316]",
    excerpt:
      "传统的产品改版依赖直觉和经验，成功率不到 30%。本文介绍如何用 AI 构建评论分析→洞察提炼→改版执行→效果验证的完整闭环，让每一次改版都有据可依。",
    sections: [
      {
        type: "paragraph",
        text: "在跨境电商行业，产品改版是一个高风险动作。改好了，销量翻倍；改砸了，库存积压、差评增多、排名下滑。传统的改版决策往往依赖产品经理的'直觉'和老板的'我觉得'，成功率据行业统计不足 30%。",
      },
      {
        type: "paragraph",
        text: "AI 正在改变这个局面。通过在改版全流程中嵌入 AI 分析，你可以从'拍脑袋改版'升级为'数据驱动改版'，显著提高改版的成功率和 ROI。",
      },
      {
        type: "h2",
        id: "traditional-pain-points",
        text: "传统改版流程的三大痛点",
      },
      {
        type: "paragraph",
        text: "痛点一：需求来源碎片化。客户邮件、社交媒体留言、QA 问答、竞品评论区……改进需求散落在十几种渠道中，没人能完整梳理。结果往往是'谁嗓门大就听谁的'，而非'哪个需求最普遍就做哪个'。",
      },
      {
        type: "paragraph",
        text: "痛点二：分析过程主观化。同样的 100 条差评，A 产品经理认为核心问题是'物流包装'，B 认为是'产品材质'。缺乏客观的数据分析框架，导致团队内部争论不休，决策周期被无限拉长。",
      },
      {
        type: "paragraph",
        text: "痛点三：效果归因模糊化。改版上线后，销量涨了——是因为改版？还是因为旺季到了？促销活动？竞品断货？缺乏干净的因果归因，导致团队无法判断改版是否真正成功，也无法将经验沉淀为可复用的方法论。",
      },
      {
        type: "blockquote",
        text: "没有闭环的改版就是赌博。AI 的价值不在于替代人类的判断，而在于为每一次判断提供可靠的数据支撑。",
      },
      {
        type: "h2",
        id: "ai-closed-loop",
        text: "AI 闭环：分析→洞察→行动→验证",
      },
      {
        type: "paragraph",
        text: "第一阶段：AI 分析。ReviewLens 的 AI 引擎可以自动采集并分析来自 Amazon、Walmart、Shopee 等多平台的评论数据，通过情感分析、主题聚类、竞品对比等模型，自动生成'产品改进建议报告'。这份报告不是原始数据的堆砌，而是经过优先级排序、附有预期收益估算的可执行建议。",
      },
      {
        type: "paragraph",
        text: "第二阶段：洞察决策。有了 AI 生成的改进建议后，产品经理带着数据（而非直觉）进入决策会议。每条建议都配有：问题影响面（多少用户受影响）、竞品对比（竞品是否也存在同样问题）、预期收益（解决后预计评分提升幅度）。团队可以快速对齐优先级，决策时间从数周缩短到数天。",
      },
      {
        type: "image",
        gradient: "from-[#e5a63b] to-[#f97316]",
        caption: "图：AI 驱动的产品改版闭环示意",
      },
      {
        type: "paragraph",
        text: "第三阶段：改版执行。将确定的改进措施转化为具体的工程/供应链任务，排入迭代计划。关键是在执行期间保持评论监控——如果改版过程中出现了新的批量问题，可以及时暂停并调整方案，避免更大损失。",
      },
      {
        type: "paragraph",
        text: "第四阶段：效果验证。改版上线后，AI 自动追踪对应问题簇的提及频率变化。如果'按键手感偏硬'的提及量从 37% 降到 5%，说明改版成功。如果没有明显变化，AI 会进一步分析原因：是方案本身无效？还是执行偏差（比如新批次仍然用了旧物料）？这种快速的因果反馈让团队可以每周迭代，而不是等一个季度后才发现改版失败。",
      },
      {
        type: "h2",
        id: "getting-started",
        text: "落地建议：如何开始你的第一个改版闭环",
      },
      {
        type: "paragraph",
        text: "第一步：选择一条产品线。不需要一开始就覆盖所有 SKU。挑选评论量最大的那条产品线（至少 100+ 条评论），跑通全流程后再横向扩展。",
      },
      {
        type: "paragraph",
        text: "第二步：建立评论基线。在改版前，记录当前各问题簇的提及频率——这是你改版后的对比基准。没有基线的改版效果评估是不完整的。",
      },
      {
        type: "paragraph",
        text: "第三步：选择一个高频问题开始。不要试图一次性解决所有问题。选 Top 1 问题，聚焦资源，快速验证闭环效果。成功后再滚动到下一个问题。",
      },
      {
        type: "paragraph",
        text: "第四步：周度回顾。每周花 30 分钟回顾评论变化：新问题出现没？老问题改善没？竞品在做什么？这个简单的习惯是闭环持续运转的发动机。",
      },
    ],
  },
};

/* ================================================================
   generateStaticParams
   ================================================================ */

export function generateStaticParams(): { slug: string }[] {
  return Object.keys(ARTICLES).map((slug) => ({ slug }));
}

/* ================================================================
   generateMetadata
   ================================================================ */

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const article = ARTICLES[slug];
  if (!article) {
    return buildMarketingMetadata({
      title: "文章未找到",
      description: "博客文章未找到",
      path: "/blog",
    });
  }
  return buildMarketingMetadata({
    title: `${article.title} — ReviewLens 博客`,
    description: article.excerpt,
    path: `/blog/${article.slug}`,
  });
}

/* ================================================================
   渲染辅助
   ================================================================ */

function SectionRenderer({ section }: { section: ArticleSection }) {
  switch (section.type) {
    case "h2":
      return (
        <h2
          id={section.id}
          className="mb-4 mt-10 border-l-[3px] border-[#f36f8f] pl-4 font-heading text-2xl font-extrabold leading-snug text-ink"
        >
          {section.text}
        </h2>
      );

    case "paragraph":
      return (
        <p className="mb-5 font-body text-base leading-[1.8] text-ink">
          {section.text}
        </p>
      );

    case "blockquote":
      return (
        <blockquote className="mb-6 border-l-[3px] border-[#8d7be8] bg-[rgba(141,123,232,0.04)] py-3 pl-5 font-body text-[15px] italic leading-[1.7] text-soft">
          {section.text}
        </blockquote>
      );

    case "image":
      return (
        <figure className="my-8">
          <div
            className={`mx-auto aspect-[800/400] w-full max-w-[800px] rounded-2xl bg-gradient-to-br ${section.gradient || "from-[#f36f8f] to-[#8d7be8]"} flex items-center justify-center`}
          >
            {/* 装饰性几何图形 */}
            <div className="absolute inset-0 overflow-hidden rounded-2xl opacity-15">
              <div className="absolute right-8 top-8 h-16 w-16 rounded-full border-2 border-white" />
              <div className="absolute bottom-8 left-8 h-20 w-20 rounded-lg border-2 border-white" />
              <div className="absolute right-16 bottom-16 h-10 w-10 rotate-45 border-2 border-white" />
              <div className="absolute left-1/2 top-1/2 h-24 w-24 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/50" />
            </div>
            <span className="relative z-10 text-sm font-medium uppercase tracking-[0.1em] text-white/40">
              {section.caption || "图片"}
            </span>
          </div>
          {section.caption && (
            <figcaption className="mt-2 text-center font-body text-[13px] text-soft">
              {section.caption}
            </figcaption>
          )}
        </figure>
      );

    default:
      return null;
  }
}

/* ================================================================
   相关文章
   ================================================================ */

function RelatedArticleCard({
  article,
}: {
  article: SeedArticle;
}) {
  return (
    <Link
      href={`/blog/${article.slug}`}
      className="glass-white group flex items-center gap-3 p-3 transition-all duration-200 hover:scale-[1.02] hover:shadow-glow"
    >
      {/* 缩略图 */}
      <div
        className={`h-[60px] w-[60px] shrink-0 rounded-lg bg-gradient-to-br ${article.gradient} flex items-center justify-center`}
      >
        <span className="text-[10px] font-medium uppercase tracking-[0.05em] text-white/40">
          封面
        </span>
      </div>
      <div className="min-w-0 flex-1">
        <p className="line-clamp-2 font-body text-[13px] font-medium leading-snug text-ink group-hover:text-rose transition-colors duration-200">
          {article.title}
        </p>
        <p className="mt-1 font-body text-[11px] text-soft">
          {article.date}
        </p>
      </div>
    </Link>
  );
}

/* ================================================================
   分享按钮行（纯展示，无 JS 分享 API）
   ================================================================ */

function ShareButtons() {
  return (
    <div className="flex items-center gap-2">
      <span className="font-body text-[12px] font-medium uppercase tracking-[0.06em] text-soft">
        分享
      </span>
      <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-line bg-white/50 text-[13px] text-soft cursor-pointer transition-colors hover:border-rose hover:text-rose select-none">
        𝕏
      </span>
      <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-line bg-white/50 text-[13px] text-soft cursor-pointer transition-colors hover:border-rose hover:text-rose select-none">
        in
      </span>
      <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-line bg-white/50 text-[13px] text-soft cursor-pointer transition-colors hover:border-rose hover:text-rose select-none">
        f
      </span>
    </div>
  );
}

/* ================================================================
   页面主体
   ================================================================ */

export default async function BlogDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = ARTICLES[slug];

  if (!article) {
    return (
      <div className="relative min-h-screen page-bg-warm overflow-hidden">
        <SiteHeader />
        <main className="relative z-10 mx-auto max-w-7xl px-6 pb-16 pt-20 text-center lg:px-10">
          <h1 className="font-heading text-3xl font-extrabold text-ink">
            文章未找到
          </h1>
          <p className="mt-4 text-soft">
            该文章不存在或已被移除。
          </p>
          <Link
            href="/blog"
            className="mt-6 inline-flex rounded-pill bg-rose px-6 py-2.5 text-sm font-semibold text-white transition-all hover:brightness-110"
          >
            返回博客首页
          </Link>
        </main>
        <SiteFooter />
      </div>
    );
  }

  /* 获取相关文章（除当前文章外的其他文章） */
  const relatedArticles = Object.values(ARTICLES).filter(
    (a) => a.slug !== article.slug,
  );

  return (
    <div className="relative min-h-screen page-bg-warm overflow-hidden">
      {/* V3 浮动 blob 装饰 */}
      <div className="blob-rose absolute -top-32 -left-32 z-0" />
      <div className="blob-lavender absolute top-40 -right-24 z-0" />

      <SiteHeader />

      <main className="relative z-10 mx-auto w-full max-w-7xl px-6 pb-16 pt-4 lg:px-10">
        {/* ================================================================
            封面图
            ================================================================ */}
        <div
          className={`relative mx-auto aspect-[800/400] w-full max-w-[800px] overflow-hidden rounded-2xl bg-gradient-to-br ${article.gradient}`}
        >
          {/* 装饰性几何图形 */}
          <div className="absolute inset-0 opacity-15">
            <div className="absolute right-10 top-10 h-20 w-20 rounded-full border-2 border-white" />
            <div className="absolute bottom-10 left-10 h-24 w-24 rounded-lg border-2 border-white" />
            <div className="absolute right-20 bottom-20 h-14 w-14 rotate-45 border-2 border-white" />
            <div className="absolute left-1/2 top-1/2 h-32 w-32 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/50" />
            <div className="absolute left-20 top-20 h-12 w-12 rounded-full border border-white/30" />
          </div>
          <span className="absolute bottom-4 right-6 z-10 text-xs font-medium uppercase tracking-[0.1em] text-white/35">
            封面图片
          </span>
        </div>

        {/* ================================================================
            标题 + Meta
            ================================================================ */}
        <header className="mx-auto mt-8 max-w-[680px] text-center">
          <h1 className="font-heading text-[36px] font-extrabold leading-[1.15] tracking-[-0.02em] text-ink">
            {article.title}
          </h1>

          {/* Meta 行 */}
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2 font-body text-sm text-soft">
            <span>{article.date}</span>
            <span className="text-line">|</span>
            <span>{article.author}</span>
            <span className="text-line">|</span>
            <span>{article.readTime}</span>
            {article.tags.map((tag) => (
              <span
                key={tag}
                className="ml-1 inline-flex rounded-pill bg-roseSoft px-2.5 py-0.5 text-[11px] font-medium text-[#d94d72]"
              >
                {tag}
              </span>
            ))}
          </div>
        </header>

        {/* ================================================================
            正文 + 侧边栏
            ================================================================ */}
        <div className="mx-auto mt-10 flex max-w-[1020px] flex-col gap-10 lg:flex-row">
          {/* 左侧：正文区域 */}
          <article className="min-w-0 flex-1">
            <div className="mx-auto max-w-[680px]">
              {article.sections.map((section, i) => (
                <SectionRenderer key={i} section={section} />
              ))}
            </div>

            {/* 移动端：相关文章 */}
            <div className="mt-12 lg:hidden">
              <h3 className="mb-4 font-heading text-lg font-bold text-ink">
                相关文章
              </h3>
              <div className="flex flex-col gap-3">
                {relatedArticles.map((ra) => (
                  <RelatedArticleCard key={ra.slug} article={ra} />
                ))}
              </div>
            </div>
          </article>

          {/* 右侧 sticky 侧边栏（桌面端 280px） */}
          <aside className="hidden w-[280px] shrink-0 lg:block">
            <div className="sticky top-24 flex flex-col gap-5">
              {/* 目录 TOC */}
              <BlogToc article={article} />

              {/* 分享按钮 */}
              <div className="glass-white p-4">
                <ShareButtons />
              </div>

              {/* 相关文章 */}
              <div className="glass-white p-4">
                <h3 className="mb-3 font-heading text-sm font-bold uppercase tracking-[0.06em] text-ink">
                  相关文章
                </h3>
                <div className="flex flex-col gap-2.5">
                  {relatedArticles.map((ra) => (
                    <RelatedArticleCard key={ra.slug} article={ra} />
                  ))}
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>

      {/* 底部：相关文章 + CTA */}
      <section className="relative z-10 mx-auto w-full max-w-7xl px-6 pb-10 lg:px-10">
        {/* 桌面端相关文章行 */}
        <div className="hidden lg:block">
          <h3 className="mb-5 font-heading text-xl font-bold text-ink">
            相关文章
          </h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {relatedArticles.map((ra) => (
              <Link
                key={ra.slug}
                href={`/blog/${ra.slug}`}
                className="glass-white group flex items-center gap-4 p-4 transition-all duration-200 hover:scale-[1.02] hover:shadow-glow"
              >
                <div
                  className={`h-[80px] w-[120px] shrink-0 rounded-lg bg-gradient-to-br ${ra.gradient} flex items-center justify-center`}
                >
                  <span className="text-[10px] font-medium uppercase tracking-[0.05em] text-white/40">
                    封面
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="line-clamp-2 font-body text-[15px] font-semibold leading-snug text-ink group-hover:text-rose transition-colors duration-200">
                    {ra.title}
                  </p>
                  <p className="mt-1.5 line-clamp-2 font-body text-[13px] leading-relaxed text-soft">
                    {ra.excerpt}
                  </p>
                  <p className="mt-1 font-body text-[11px] text-soft/60">
                    {ra.date} · {ra.readTime}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <BottomCta
        text="让 AI 帮你分析评论"
        buttonLabel="免费试用"
        buttonHref="/register"
      />

      <SiteFooter />
    </div>
  );
}
