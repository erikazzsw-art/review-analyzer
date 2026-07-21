"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ProductOverview } from "@/lib/api/types";
import { DeleteProductButton } from "@/components/products/delete-product-button";

type PlatformFilter = "all" | "amazon" | "aliexpress" | "shopee" | "ebay" | "walmart";

function normalizePlatform(platform: string | null): PlatformFilter {
  if (!platform) return "all";
  const lower = platform.toLowerCase();
  if (lower.includes("aliexpress")) return "aliexpress";
  if (lower.includes("shopee")) return "shopee";
  if (lower.includes("ebay")) return "ebay";
  if (lower.includes("walmart")) return "walmart";
  if (lower.includes("amazon")) return "amazon";
  return "all";
}

function getPlatformBadge(platform: string | null) {
  const norm = normalizePlatform(platform);
  if (norm === "amazon") return { label: "Amazon", color: "bg-orange-50 text-orange-700 border-orange-200" };
  if (norm === "aliexpress") return { label: "AliExpress", color: "bg-red-50 text-red-700 border-red-200" };
  if (norm === "shopee") return { label: "Shopee", color: "bg-green-50 text-green-700 border-green-200" };
  if (norm === "ebay") return { label: "eBay", color: "bg-blue-50 text-blue-700 border-blue-200" };
  if (norm === "walmart") return { label: "Walmart", color: "bg-sky-50 text-sky-700 border-sky-200" };
  return null;
}

function StarRating({ rating }: { rating: number | null }) {
  if (rating == null) return <span className="text-xs text-soft">—</span>;
  const fullStars = Math.floor(rating);
  const hasHalf = rating - fullStars >= 0.3;
  return (
    <div className="flex items-center gap-1">
      <div className="flex" aria-label={`${rating} stars`}>
        {Array.from({ length: 5 }, (_, i) => (
          <svg key={i} className={`h-3.5 w-3.5 ${i < fullStars ? "text-amber-400" : i === fullStars && hasHalf ? "text-amber-300" : "text-gray-200"}`} fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        ))}
      </div>
      <span className="text-xs font-semibold text-ink/70">{rating.toFixed(1)}</span>
    </div>
  );
}

function ProductRow({
  product,
  expanded,
  onToggle,
  t,
}: {
  product: ProductOverview;
  expanded: boolean;
  onToggle: () => void;
  t: (key: string, values?: Record<string, string | number | Date>) => string;
}) {
  const title = product.name || product.parent_product_id;
  const badge = getPlatformBadge(product.platform);
  const hasVariants = (product.variants?.length ?? 0) > 0;
  const Chevron = expanded ? ChevronDown : ChevronRight;

  return (
    <>
      <tr className="group border-b border-line transition hover:bg-gray-50/60">
        <td className="w-10 px-3 py-3">
          {hasVariants ? (
            <button
              type="button"
              onClick={onToggle}
              className="inline-flex items-center justify-center rounded p-0.5 text-soft transition hover:bg-gray-100 hover:text-ink"
              aria-label={expanded ? t("tree.collapse") : t("tree.expand")}
            >
              <Chevron className="h-4 w-4" />
            </button>
          ) : (
            <span className="inline-block w-5" />
          )}
        </td>
        <td className="px-3 py-3">
          <div className="flex items-center gap-2">
            {product.image_url ? (
              <img src={product.image_url} alt={title} className="h-9 w-9 rounded border border-line object-contain" />
            ) : (
              <div className="flex h-9 w-9 items-center justify-center rounded border border-line bg-gray-50">
                <svg className="h-5 w-5 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
            )}
            <div>
              <Link
                href={`/products/${product.id}`}
                className="text-sm font-bold text-ink hover:text-[#f36f8f] transition"
              >
                {title}
              </Link>
              {product.brand && (
                <p className="text-xs text-soft">{product.brand}</p>
              )}
            </div>
          </div>
        </td>
        <td className="px-3 py-3">
          {badge && (
            <span className={`inline-flex rounded-pill border px-2 py-0.5 text-[10px] font-bold ${badge.color}`}>
              {badge.label}
            </span>
          )}
        </td>
        <td className="px-3 py-3 text-center">
          <StarRating rating={product.rating} />
        </td>
        <td className="px-3 py-3 text-center text-sm font-semibold text-ink">
          {product.reviews_total ?? product.review_count}
        </td>
        <td className="px-3 py-3 text-center text-sm font-semibold text-ink">
          {product.variant_count}
        </td>
        <td className="px-3 py-3">
          {product.session_count > 0 && (
            <span className="inline-flex rounded-pill bg-[#fff0f5] px-2 py-0.5 text-[10px] font-semibold text-[#f36f8f]">
              {t("grid.hasAnalysis")}
            </span>
          )}
        </td>
        <td className="px-3 py-3 text-right">
          <div className="flex items-center justify-end gap-1">
            <Link
              href={`/products/${product.id}`}
              className="rounded-pill border border-line bg-white px-3 py-1 text-xs font-semibold text-ink transition hover:border-ink/30"
            >
              {t("tree.viewDetail")}
            </Link>
            {product.id != null && (
              <DeleteProductButton productId={product.id} productName={title} />
            )}
          </div>
        </td>
      </tr>
      {/* Child ASIN rows */}
      {expanded && hasVariants && (
        <>
          {product.variants!.map((v, idx) => (
            <tr key={`${v.id ?? idx}-child`} className="border-b border-line bg-[#faf8fb]">
              <td className="w-10 px-3 py-2" />
              <td className="px-3 py-2 pl-12">
                <span className="inline-flex items-center gap-1.5">
                  <svg className="h-3 w-3 text-soft/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                  <div className="flex items-center gap-2">
                    {v.image_url ? (
                      <img src={v.image_url as string} alt="" className="h-7 w-7 rounded border border-line object-contain" />
                    ) : (
                      <div className="flex h-7 w-7 items-center justify-center rounded border border-line bg-gray-50">
                        <svg className="h-4 w-4 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16" />
                        </svg>
                      </div>
                    )}
                    <div>
                      <span className="text-xs font-mono text-ink/70">
                        {v.child_asin || "—"}
                      </span>
                      {(v.name || v.variant_sku) && (
                        <span className="ml-2 text-xs text-soft">
                          {v.name || v.variant_sku}
                        </span>
                      )}
                    </div>
                  </div>
                </span>
              </td>
              <td className="px-3 py-2" />
              <td className="px-3 py-2" />
              <td className="px-3 py-2" />
              <td className="px-3 py-2" />
              <td className="px-3 py-2" />
              <td className="px-3 py-2" />
            </tr>
          ))}
        </>
      )}
    </>
  );
}

export function ProductTreeView({ products }: { products: ProductOverview[] }) {
  const t = useTranslations("products");
  const [filter, setFilter] = useState<PlatformFilter>("all");
  const [expandedIds, setExpandedIds] = useState<Set<number | string>>(new Set());

  const PLATFORM_TABS = [
    { value: "all" as const, label: t("grid.tabAll") },
    { value: "amazon" as const, label: "Amazon" },
    { value: "aliexpress" as const, label: "AliExpress" },
    { value: "shopee" as const, label: "Shopee" },
    { value: "ebay" as const, label: "eBay" },
    { value: "walmart" as const, label: "Walmart" },
  ];

  const filtered = useMemo(() => {
    if (filter === "all") return products;
    return products.filter((p) => normalizePlatform(p.platform) === filter);
  }, [products, filter]);

  function toggleExpand(productId: number | null) {
    const key = productId ?? "unknown";
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  return (
    <div className="space-y-4">
      {/* Platform filter tabs */}
      <div className="flex gap-1 rounded-card border border-line p-1 w-fit">
        {PLATFORM_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => setFilter(tab.value)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition ${
              filter === tab.value
                ? "bg-ink text-white shadow-sm"
                : "text-ink/60 hover:text-ink hover:bg-gray-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tree table */}
      {filtered.length > 0 ? (
        <div className="rounded-shell border border-line bg-white/90 shadow-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-line bg-[#fafafa] text-left text-xs font-semibold uppercase tracking-wider text-soft">
                <th className="w-10 px-3 py-3" />
                <th className="px-3 py-3">{t("tree.colProduct")}</th>
                <th className="px-3 py-3">{t("tree.colPlatform")}</th>
                <th className="px-3 py-3 text-center">{t("tree.colRating")}</th>
                <th className="px-3 py-3 text-center">{t("tree.colReviews")}</th>
                <th className="px-3 py-3 text-center">{t("tree.colVariants")}</th>
                <th className="px-3 py-3">{t("tree.colStatus")}</th>
                <th className="px-3 py-3 text-right">{t("tree.colActions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {filtered.map((product) => (
                <ProductRow
                  key={`${product.parent_product_id}-${product.id ?? "archived"}`}
                  product={product}
                  expanded={expandedIds.has(product.id ?? "unknown")}
                  onToggle={() => toggleExpand(product.id)}
                  t={t}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-soft py-8 text-center">{t("grid.noProductsInPlatform")}</p>
      )}
    </div>
  );
}
