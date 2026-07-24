import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { CreateProductButton } from "@/components/products/create-product-button";
import { ImportProductsButton } from "@/components/products/import-products-button";
import { ProductTreeView } from "@/components/products/product-tree-view";
import { getProducts, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";
import { getTranslations } from "next-intl/server";

export async function generateMetadata() {
  const t = await getTranslations("products.page");
  return buildNoIndexMetadata({
    title: t("metaTitle"),
    description: t("metaDescription"),
  });
}

export default async function ProductsPage() {
  const t = await getTranslations("products");

  try {
    const response = await getProducts();
    return (
      <AppShell
        currentPath="/products"
        title={t("page.title")}
        description={t("page.description")}
      >
        <div className="flex items-center justify-between gap-4">
          <section className="grid flex-1 gap-4 md:grid-cols-3">
            <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                {t("page.totalProducts")}
              </div>
              <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
                {response.total}
              </div>
            </div>
            <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                {t("page.totalReviews")}
              </div>
              <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
                {response.items.reduce((sum, p) => sum + p.review_count, 0)}
              </div>
            </div>
            <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                {t("page.totalVariants")}
              </div>
              <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
                {response.items.reduce((sum, p) => sum + p.variant_count, 0)}
              </div>
            </div>
          </section>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <ImportProductsButton />
            <CreateProductButton />
          </div>
        </div>

        {response.items.length > 0 ? (
          <ProductTreeView products={response.items} />
        ) : (
          <section className="rounded-shell border border-dashed border-line bg-white/80 px-6 py-10 shadow-card backdrop-blur">
            <h2 className="font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
              {t("page.emptyTitle")}
            </h2>
            <p className="mt-3 max-w-2xl text-base leading-8 text-soft">
              {t("page.emptyDescription")}
            </p>
            <div className="mt-6">
              <div className="flex flex-wrap gap-2">
                <ImportProductsButton />
                <CreateProductButton />
              </div>
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
          title={t("page.loginTitle")}
          description={t("page.loginDescription")}
        >
          <EmptyAuthState
            title={t("page.loginEmptyTitle")}
            description={t("page.loginEmptyDesc")}
          />
        </AppShell>
      );
    }

    throw error;
  }
}
