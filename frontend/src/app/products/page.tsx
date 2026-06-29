import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { CreateProductButton } from "@/components/products/create-product-button";
import { DeleteProductButton } from "@/components/products/delete-product-button";
import { getProducts, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";
import type { ProductOverview } from "@/lib/api/types";
import Link from "next/link";

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

function StarRating({ rating }: { rating: number | null }) {
  if (rating == null) return <span className="text-xs text-soft">暂无评分</span>;
  const fullStars = Math.floor(rating);
  const hasHalf = rating - fullStars >= 0.3;
  return (
    <div className="flex items-center gap-1">
      <div className="flex" aria-label={`${rating} stars`}>
        {Array.from({ length: 5 }, (_, i) => (
          <svg key={i} className={`h-4 w-4 ${i < fullStars ? "text-amber-400" : i === fullStars && hasHalf ? "text-amber-300" : "text-gray-200"}`} fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        ))}
      </div>
      <span className="text-xs font-semibold text-ink/70">{rating.toFixed(1)}</span>
    </div>
  );
}

function ProductCard({ product }: { product: ProductOverview }) {
  const title = product.name || product.parent_product_id;
  const lifecycle =
    lifecycleLabels[product.lifecycle_stage || ""] ||
    product.lifecycle_stage ||
    "";

  return (
    <div className="group relative flex flex-col overflow-hidden rounded-shell border border-line bg-white/90 shadow-card backdrop-blur transition hover:border-[#f36f8f]/40 hover:shadow-lg">
      <Link
        href={`/products/${product.id}`}
        className="absolute inset-0 z-0"
        aria-label={`查看 ${title} 详情`}
      />

      {/* 产品图片区域 */}
      <div className="relative aspect-square w-full overflow-hidden bg-gray-50">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={title}
            className="h-full w-full object-contain p-3 transition group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <svg className="h-16 w-16 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        )}

        {/* 查看分析按钮 */}
        {product.session_count > 0 && (
          <span
            className="absolute right-2 top-2 rounded-pill bg-white/90 px-2.5 py-1 text-[11px] font-semibold text-[#f36f8f] shadow-sm backdrop-blur"
          >
            有分析
          </span>
        )}

        {/* 生命周期 badge */}
        {lifecycle && (
          <span className="absolute bottom-2 left-2 rounded-pill bg-white/90 px-2 py-0.5 text-[10px] font-bold tracking-wide text-ink/70 backdrop-blur">
            {lifecycle}
          </span>
        )}
      </div>

      {/* 产品信息区域 */}
      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3 className="line-clamp-2 text-sm font-bold leading-5 text-ink group-hover:text-[#f36f8f]">
          {title}
        </h3>

        {product.brand && (
          <p className="text-xs text-soft">{product.brand}</p>
        )}

        <StarRating rating={product.rating} />

        <div className="mt-auto flex items-center justify-between pt-2 text-xs text-soft">
          <span>{product.reviews_total ?? product.review_count} 条评论</span>
          <span>{product.variant_count} 个变体</span>
        </div>

        {/* 删除按钮 — z-10 浮于 overlay link 之上 */}
        <div className="relative z-10 mt-2 flex justify-end">
          {product.id != null && (
            <DeleteProductButton productId={product.id} productName={title} />
          )}
        </div>
      </div>
    </div>
  );
}

export default async function ProductsPage() {
  try {
    const response = await getProducts();
    return (
      <AppShell
        currentPath="/products"
        title="产品管理"
        description="浏览所有产品档案，点击卡片查看详情和变体信息。"
      >
        <div className="flex items-center justify-between gap-4">
          <section className="grid flex-1 gap-4 md:grid-cols-3">
            <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                产品总数
              </div>
              <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
                {response.total}
              </div>
            </div>
            <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                总评论数
              </div>
              <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
                {response.items.reduce((sum, p) => sum + (p.reviews_total ?? p.review_count), 0)}
              </div>
            </div>
            <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                总变体数
              </div>
              <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
                {response.items.reduce((sum, p) => sum + p.variant_count, 0)}
              </div>
            </div>
          </section>
          <CreateProductButton />
        </div>

        {response.items.length > 0 ? (
          <section className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
              当前账号下还没有产品组。通过 ASIN 抓取评论时会自动创建产品档案，或点击右上角手动添加。
            </p>
            <div className="mt-6">
              <CreateProductButton />
            </div>
          </section>
        )}
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/products"
          title="产品管理"
          description="登录后查看产品档案。"
        >
          <EmptyAuthState
            title="登录后查看产品组、变体和评论资产"
            description="登录后可以看到从 ASIN 抓取自动沉淀的产品数据。"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
