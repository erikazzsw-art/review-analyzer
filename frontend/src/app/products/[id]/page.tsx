import { AppShell } from "@/components/app/app-shell";
import { DeleteVariantButton } from "@/components/products/delete-variant-button";
import { getProductDetail, isApiError } from "@/lib/api/server";
import Link from "next/link";
import { notFound } from "next/navigation";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function ProductDetailPage({ params }: Props) {
  const { id } = await params;
  const productId = parseInt(id, 10);
  if (isNaN(productId)) notFound();

  try {
    const { product, variants } = await getProductDetail(productId);

    const name = (product.name as string) || (product.parent_product_id as string) || "未命名产品";
    const brand = product.brand as string | null;
    const rating = product.rating != null ? Number(product.rating) : null;
    const imageUrl = product.image_url as string | null;
    const parentProductId = product.parent_product_id as string;
    const category = product.category as string | null;
    const ratingsTotal = product.ratings_total as number | null;
    const reviewsTotal = product.reviews_total as number | null;

    return (
      <AppShell currentPath="/products" title={name} description="产品详情与变体列表">
        {/* 产品头部信息 */}
        <div className="rounded-shell border border-line bg-white/90 p-6 shadow-card backdrop-blur">
          <div className="flex flex-col gap-6 md:flex-row md:items-start">
            {/* 产品图片 */}
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

            {/* 产品信息 */}
            <div className="flex-1">
              <h1 className="font-heading text-2xl font-extrabold tracking-[-0.03em] text-ink">
                {name}
              </h1>
              {brand && <p className="mt-1 text-sm text-soft">品牌：{brand}</p>}
              {category && <p className="mt-1 text-sm text-soft">类目：{category}</p>}
              <p className="mt-1 text-sm text-soft">ASIN：{parentProductId}</p>

              {/* 评分 */}
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
                    <span className="text-xs text-soft">({ratingsTotal} 评分)</span>
                  )}
                </div>
              )}

              {reviewsTotal != null && (
                <p className="mt-2 text-sm text-soft">{reviewsTotal} 条评论</p>
              )}

              {/* 操作按钮 */}
              <div className="mt-4 flex flex-wrap gap-3">
                <Link
                  href={`/analysis/results?product_id=${parentProductId}`}
                  className="inline-flex items-center rounded-pill bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-card transition hover:opacity-90"
                >
                  查看评论分析
                </Link>
                <Link
                  href="/products"
                  className="inline-flex items-center rounded-pill border border-line bg-white px-5 py-2.5 text-sm font-semibold text-ink transition hover:bg-gray-50"
                >
                  返回产品列表
                </Link>
              </div>
            </div>
          </div>
        </div>

        {/* 变体表格 */}
        <div className="rounded-shell border border-line bg-white/90 p-6 shadow-card backdrop-blur">
          <h2 className="font-heading text-lg font-bold text-ink">
            变体列表 ({variants.length})
          </h2>

          {variants.length > 0 ? (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs font-semibold uppercase tracking-wider text-soft">
                    <th className="px-3 py-3">图片</th>
                    <th className="px-3 py-3">ASIN</th>
                    <th className="px-3 py-3">变体名</th>
                    <th className="px-3 py-3">品牌</th>
                    <th className="px-3 py-3">价格</th>
                    <th className="px-3 py-3">销量</th>
                    <th className="px-3 py-3">销售额</th>
                    <th className="px-3 py-3">FBA</th>
                    <th className="px-3 py-3">上架日期</th>
                    <th className="px-3 py-3">操作</th>
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
                      <td className="max-w-[200px] truncate px-3 py-3">{(v.name as string) || (v.variant_sku as string) || "—"}</td>
                      <td className="px-3 py-3">{(v.brand as string) || "—"}</td>
                      <td className="px-3 py-3">
                        {(v.price as number) != null
                          ? `${(v.price_currency as string) || "$"}${(v.price as number).toFixed(2)}`
                          : "—"}
                      </td>
                      <td className="px-3 py-3 text-soft">—</td>
                      <td className="px-3 py-3 text-soft">—</td>
                      <td className="px-3 py-3 text-soft">—</td>
                      <td className="px-3 py-3 text-soft">{(v.listing_date as string) || "—"}</td>
                      <td className="px-3 py-3">
                        <DeleteVariantButton
                          productId={productId}
                          variantId={v.id as number}
                          variantName={(v.name as string) || (v.child_asin as string) || "未命名变体"}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-4 text-sm text-soft">
              暂无变体数据。通过 ASIN 抓取时勾选「抓取所有变体」可自动填充。
            </p>
          )}
        </div>
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 404) {
      notFound();
    }
    throw error;
  }
}
