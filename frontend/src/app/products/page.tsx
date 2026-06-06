import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { getProducts, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";
import type { ProductOverview } from "@/lib/api/types";

export const metadata = buildNoIndexMetadata({
  title: "Product Management | ClueAI",
  description: "Authenticated product groups, variants, and review assets.",
});

const lifecycleLabels: Record<string, string> = {
  research: "调研期",
  launch: "新品期",
  growth: "成长期",
  mature: "成熟期",
  decline: "衰退期",
};

const roleLabels: Record<string, string> = {
  "运营": "运营",
  "产研": "产研",
  "质检": "质检",
  "管理者": "管理者",
  "跨团队": "跨团队",
};

function metricTone(negativeRate: number): string {
  if (negativeRate >= 20) {
    return "text-[#d94d72]";
  }
  if (negativeRate >= 12) {
    return "text-[#b57a20]";
  }
  return "text-[#4b8f82]";
}

function ProductCard({ product }: { product: ProductOverview }) {
  const title = product.name || product.parent_product_id;
  const lifecycle =
    lifecycleLabels[product.lifecycle_stage || ""] ||
    product.lifecycle_stage ||
    "未设置";
  const owner = product.owner_role
    ? roleLabels[product.owner_role] || product.owner_role
    : "未设置";

  return (
    <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="inline-flex rounded-pill bg-roseSoft px-3 py-1 text-[11px] font-bold tracking-[0.12em] text-[#d94d72]">
            {product.is_archived_from_sessions ? "历史评论沉淀" : "正式产品组"}
          </div>
          <h2 className="mt-4 font-heading text-[1.9rem] font-extrabold tracking-[-0.04em] text-ink">
            {title}
          </h2>
          <p className="mt-2 text-sm leading-7 text-soft">
            父体产品编号：{product.parent_product_id}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-soft">
            {product.platform || "未设置平台"}
          </span>
          <span className="rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-soft">
            {lifecycle}
          </span>
          <span className="rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-soft">
            版本 {product.current_version}
          </span>
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-card border border-line bg-[#fffafc] px-4 py-4">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
            评论总量
          </div>
          <div className="mt-2 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
            {product.review_count}
          </div>
        </div>
        <div className="rounded-card border border-line bg-[#fbfcff] px-4 py-4">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
            好评率
          </div>
          <div className="mt-2 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
            {product.positive_rate.toFixed(1)}%
          </div>
        </div>
        <div className="rounded-card border border-line bg-[#fff8f9] px-4 py-4">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
            差评率
          </div>
          <div
            className={[
              "mt-2 font-heading text-3xl font-extrabold tracking-[-0.04em]",
              metricTone(product.negative_rate),
            ].join(" ")}
          >
            {product.negative_rate.toFixed(1)}%
          </div>
        </div>
        <div className="rounded-card border border-line bg-[#faf8ff] px-4 py-4">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
            待复盘
          </div>
          <div className="mt-2 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
            {product.pending_review_count}
          </div>
        </div>
        <div className="rounded-card border border-line bg-[#f8fffc] px-4 py-4">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
            变体 SKU
          </div>
          <div className="mt-2 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
            {product.variant_count}
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-card border border-line bg-white/88 p-5">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                类目
              </div>
              <div className="mt-2 text-sm leading-7 text-ink">
                {product.category || "未设置"}
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                负责人
              </div>
              <div className="mt-2 text-sm leading-7 text-ink">{owner}</div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                生产周期
              </div>
              <div className="mt-2 text-sm leading-7 text-ink">
                {product.production_cycle_days
                  ? `${product.production_cycle_days} 天`
                  : "未设置"}
              </div>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            <div className="rounded-card border border-line bg-[#fff9fa] px-4 py-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                最大问题
              </div>
              <div className="mt-2 text-sm leading-7 text-ink">
                {product.top_issue || "暂无问题标签"}
              </div>
            </div>
            <div className="rounded-card border border-line bg-[#fbf9ff] px-4 py-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                最大亮点
              </div>
              <div className="mt-2 text-sm leading-7 text-ink">
                {product.top_highlight || "暂无亮点标签"}
              </div>
            </div>
          </div>

          {product.core_selling_points ? (
            <div className="mt-5 rounded-card border border-line bg-white px-4 py-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                核心卖点
              </div>
              <p className="mt-2 text-sm leading-7 text-ink">
                {product.core_selling_points}
              </p>
            </div>
          ) : null}

          {product.main_competitors ? (
            <div className="mt-4 rounded-card border border-line bg-white px-4 py-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                主要竞品
              </div>
              <p className="mt-2 text-sm leading-7 text-ink">
                {product.main_competitors}
              </p>
            </div>
          ) : null}
        </div>

        <div className="rounded-card border border-line bg-white/90 p-5">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
            最近批次
          </div>
          <div className="mt-2 text-sm leading-7 text-ink">
            {product.latest_session_label || "暂无上传批次"}
          </div>
          <div className="mt-4 text-xs font-semibold uppercase tracking-[0.12em] text-soft">
            版本 / 批次数
          </div>
          <div className="mt-2 text-sm leading-7 text-ink">
            {product.versions.length} 个版本记录 · {product.session_count} 个评论批次
          </div>

          <div className="mt-5">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              变体列表
            </div>
            {product.variants.length > 0 ? (
              <div className="mt-3 space-y-3">
                {product.variants.slice(0, 4).map((variant) => (
                  <div
                    key={`${product.parent_product_id}-${variant.id ?? variant.variant_sku}`}
                    className="rounded-card border border-line bg-[#fffafb] px-4 py-4"
                  >
                    <div className="text-sm font-semibold text-ink">
                      {variant.variant_sku || "未命名变体"}
                    </div>
                    <div className="mt-1 text-xs leading-6 text-soft">
                      {variant.child_asin || "无 Child ASIN"} ·{" "}
                      {variant.color || "无颜色"} · {variant.size || "无尺码"}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm leading-7 text-soft">
                当前还没有绑定变体。这个产品组仍然可以承接历史评论和后续行动闭环。
              </p>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}

export default async function ProductsPage() {
  try {
    const response = await getProducts();
    return (
      <AppShell
        currentPath="/products"
        title="把评论资产先沉淀到产品组，再决定哪些 SKU 值得继续改。"
        description="这一页优先展示产品组、风险指标、变体和最近批次，帮助你从分散的评论批次切回产品经营视角。当前实现对齐现有 Streamlit 的只读口径，先把资产看清楚。"
      >
        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              产品组总数
            </div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {response.total}
            </div>
          </div>
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              历史沉淀产品
            </div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {response.items.filter((item) => item.is_archived_from_sessions).length}
            </div>
          </div>
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              高风险产品
            </div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {response.items.filter((item) => item.negative_rate >= 12).length}
            </div>
          </div>
        </section>

        {response.items.length > 0 ? (
          <section className="space-y-5">
            {response.items.map((product) => (
              <ProductCard
                key={`${product.parent_product_id}-${product.id ?? "archived"}`}
                product={product}
              />
            ))}
          </section>
        ) : (
          <section className="rounded-shell border border-dashed border-line bg-white/80 px-6 py-10 shadow-card backdrop-blur">
            <h2 className="font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
              还没有产品档案
            </h2>
            <p className="mt-3 max-w-2xl text-base leading-8 text-soft">
              当前账号下还没有可展示的产品组。等 `NX-M4` 迁移上传流程后，这里会自然承接评论批次、产品绑定和版本资产。
            </p>
          </section>
        )}
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/products"
          title="产品管理已经接入真实 API，但需要登录后才能读到数据。"
          description="当前 Next.js 端已经具备读取产品资产的能力。登录表单会在后续模块继续接上，这一版先保证工作台和产品管理页的读取链路成立。"
        >
          <EmptyAuthState
            title="登录后查看产品组、风险 SKU 和变体沉淀"
            description="一旦存在有效 Cookie，这个页面会直接从 FastAPI 读取现有 Supabase 数据，不依赖 Streamlit 的页面状态。"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
