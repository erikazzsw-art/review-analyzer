import { AppShell } from "@/components/app/app-shell";
import { DeleteVariantButton } from "@/components/products/delete-variant-button";
import { EditProductButton } from "@/components/products/edit-product-button";
import { MoveVariantButton } from "@/components/products/move-variant-button";
import { ProductDetailTabs } from "@/components/products/product-detail-tabs";
import { getProductDetail, isApiError } from "@/lib/api/server";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function ProductDetailPage({ params }: Props) {
  const { id } = await params;
  const productId = parseInt(id, 10);
  if (isNaN(productId)) notFound();

  const t = await getTranslations("products");

  try {
    const { product, variants } = await getProductDetail(productId);

    const name = (product.name as string) || (product.parent_product_id as string) || t("detail.unnamedProduct");
    const brand = product.brand as string | null;
    const rating = product.rating != null ? Number(product.rating) : null;
    const imageUrl = product.image_url as string | null;
    const parentProductId = product.parent_product_id as string;
    const category = product.category as string | null;
    const ratingsTotal = product.ratings_total as number | null;
    const reviewsTotal = product.reviews_total as number | null;

    return (
      <AppShell currentPath="/products" title={name} description={t("detail.pageDescription")}>
        {/* Product header */}
        <div className="rounded-shell border border-line bg-white/90 p-6 shadow-card backdrop-blur">
          <div className="flex flex-col gap-6 md:flex-row md:items-start">
            {/* Product image */}
            <div className="h-48 w-48 flex-shrink-0 overflow-hidden rounded-card border border-line bg-gray-50">
              {imageUrl ? (
                <img src={imageUrl} alt={name} className="h-full w-full object-contain p-2" />
              ) : (
                <div className="flex h-full w-full items-center justify-center">
                  <svg className="h-20 w-20 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              )}
            </div>

            {/* Product info */}
            <div className="flex-1">
              <h1 className="font-heading text-2xl font-extrabold tracking-[-0.03em] text-ink">
                {name}
              </h1>
              {brand && <p className="mt-1 text-sm text-soft">{t("detail.brand")}：{brand}</p>}
              {category && <p className="mt-1 text-sm text-soft">{t("detail.category")}：{category}</p>}
              <p className="mt-1 text-sm text-soft">{t("detail.asin")}：{parentProductId}</p>

              {/* Rating */}
              {rating != null && (
                <div className="mt-3 flex items-center gap-2">
                  <div className="flex">
                    {Array.from({ length: 5 }, (_, i) => (
                      <svg key={i} className={`h-5 w-5 ${i < Math.floor(rating) ? "text-amber-400" : "text-gray-200"}`} fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                    ))}
                  </div>
                  <span className="text-sm font-semibold text-ink">{rating.toFixed(1)}</span>
                  {ratingsTotal != null && (
                    <span className="text-xs text-soft">{t("detail.ratingCount", { count: ratingsTotal })}</span>
                  )}
                </div>
              )}

              {reviewsTotal != null && (
                <p className="mt-2 text-sm text-soft">{t("detail.reviewCount", { count: reviewsTotal })}</p>
              )}

              {/* Action buttons */}
              <div className="mt-4 flex flex-wrap gap-3">
                <Link
                  href={`/analysis/results?product_id=${parentProductId}`}
                  className="inline-flex items-center rounded-pill bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-card transition hover:opacity-90"
                >
                  {t("detail.viewAnalysis")}
                </Link>
                <Link
                  href="/products"
                  className="inline-flex items-center rounded-pill border border-line bg-white px-5 py-2.5 text-sm font-semibold text-ink transition hover:bg-gray-50"
                >
                  {t("detail.backToList")}
                </Link>
                <EditProductButton
                  productId={productId}
                  initial={{
                    parent_product_id: parentProductId,
                    name: (product.name as string | null) ?? undefined,
                    platform: (product.platform as string | null) ?? undefined,
                    category: category ?? undefined,
                    lifecycle_stage: (product.lifecycle_stage as string | null) ?? undefined,
                    current_version: (product.current_version as string | null) ?? undefined,
                    core_selling_points: (product.core_selling_points as string | null) ?? undefined,
                    main_competitors: (product.main_competitors as string | null) ?? undefined,
                    owner_role: (product.owner_role as string | null) ?? undefined,
                    production_cycle_days: (product.production_cycle_days as number | null) ?? undefined,
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* 5.8.2: 父变体 & 子 ASIN 管理 — Tab 切换 */}
        <ProductDetailTabs
          productId={productId}
          variantCount={variants.length}
          labels={{
            tabVariants: t("detail.tabVariants"),
            tabAnalysis: t("detail.tabAnalysis"),
            totalReviews: t("detail.totalReviews"),
            positive: t("detail.positive"),
            negative: t("detail.negative"),
            unrecognizable: t("detail.unrecognizable"),
            dateRange: t("detail.dateRange"),
            inProgress: t("detail.inProgress"),
            noData: t("detail.noData"),
            noDataDesc: t("detail.noDataDesc"),
            loading: t("detail.loading"),
            error: t("detail.loadError"),
          }}
        >
          {/* Variant table — variants tab content */}
          <div>
            <h2 className="font-heading text-lg font-bold text-ink">
              {t("detail.variantList", { count: variants.length })}
            </h2>

            {variants.length > 0 ? (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs font-semibold uppercase tracking-wider text-soft">
                    <th className="px-3 py-3">{t("detail.tableImage")}</th>
                    <th className="px-3 py-3">{t("detail.tableAsin")}</th>
                    <th className="px-3 py-3">{t("detail.tableColor")}</th>
                    <th className="px-3 py-3">{t("detail.tableSize")}</th>
                    <th className="px-3 py-3">{t("detail.tableStyle")}</th>
                    <th className="px-3 py-3">{t("detail.tableMaterial")}</th>
                    <th className="px-3 py-3">{t("detail.tableVariantName")}</th>
                    <th className="px-3 py-3">{t("detail.tableBrand")}</th>
                    <th className="px-3 py-3">{t("detail.tablePrice")}</th>
                    <th className="px-3 py-3">{t("detail.tableSales")}</th>
                    <th className="px-3 py-3">{t("detail.tableRevenue")}</th>
                    <th className="px-3 py-3">{t("detail.tableFba")}</th>
                    <th className="px-3 py-3">{t("detail.tableListDate")}</th>
                    <th className="px-3 py-3">{t("detail.tableActions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {variants.map((v, idx) => (
                    <tr key={(v.id as number) ?? idx} className="transition hover:bg-gray-50/50">
                      <td className="px-3 py-3">
                        {(v.image_url as string) ? (
                          <img src={v.image_url as string} alt="" className="h-10 w-10 rounded border border-line object-contain" />
                        ) : (
                          <div className="flex h-10 w-10 items-center justify-center rounded border border-line bg-gray-50">
                            <svg className="h-5 w-5 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14" />
                            </svg>
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-3 font-mono text-xs">{(v.child_asin as string) || "—"}</td>
                      <td className="px-3 py-3 text-xs">{(v.color as string) || "—"}</td>
                      <td className="px-3 py-3 text-xs">{(v.size as string) || "—"}</td>
                      <td className="px-3 py-3 text-xs">{(v.style as string) || "—"}</td>
                      <td className="px-3 py-3 text-xs">{(v.material as string) || "—"}</td>
                      <td className="max-w-[200px] truncate px-3 py-3">{(v.name as string) || (v.variant_sku as string) || "—"}</td>
                      <td className="px-3 py-3">{(v.brand as string) || "—"}</td>
                      <td className="px-3 py-3">
                        {(v.price as number) != null
                          ? `${(v.price_currency as string) || "$"}${(v.price as number).toFixed(2)}`
                          : "—"}
                      </td>
                      <td className="px-3 py-3">{(v.sales_volume != null) ? String(v.sales_volume) : "—"}</td>
                      <td className="px-3 py-3">{v.sales_revenue != null ? `${(v.price_currency as string) || "$"}${(v.sales_revenue as number).toFixed(2)}` : "—"}</td>
                      <td className="px-3 py-3">{(v.is_fba as boolean) ? "FBA" : "FBM"}</td>
                      <td className="px-3 py-3">{(v.listing_date as string) || "—"}</td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-1">
                          <MoveVariantButton
                            productId={productId}
                            variantId={v.id as number}
                            variantName={(v.name as string) || (v.child_asin as string) || t("detail.unnamedVariant")}
                          />
                          <DeleteVariantButton
                            productId={productId}
                            variantId={v.id as number}
                            variantName={(v.name as string) || (v.child_asin as string) || t("detail.unnamedVariant")}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-4 text-sm text-soft">
              {t("detail.noVariants")}
            </p>
          )}
          </div>
        </ProductDetailTabs>
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 404) {
      notFound();
    }
    throw error;
  }
}
