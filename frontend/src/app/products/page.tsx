import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { CreateProductButton } from "@/components/products/create-product-button";
import { ProductGridWithFilter } from "@/components/products/product-grid-with-filter";
import { getProducts, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Product Management | ClueAI",
  description: "Authenticated product groups, variants, and review assets.",
});

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
          <ProductGridWithFilter products={response.items} />
        ) : (
          <section className="rounded-shell border border-dashed border-line bg-white/80 px-6 py-10 shadow-card backdrop-blur">
            <h2 className="font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
              还没有产品档案
            </h2>
            <p className="mt-3 max-w-2xl text-base leading-8 text-soft">
              当前账号下还没有产品组。通过产品编码抓取评论时会自动创建产品档案，或点击右上角手动添加。
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
            description="登录后可以看到从产品编码抓取自动沉淀的产品数据。"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
