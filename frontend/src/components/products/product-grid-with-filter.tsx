"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { ProductOverview } from "@/lib/api/types";
import { DeleteProductButton } from "@/components/products/delete-product-button";

type PlatformFilter = "all" | "amazon" | "aliexpress" | "shopee" | "ebay" | "walmart";

const lifecycleKeys: Record<string, string> = {
  research: "lifecycleResearch",
  launch: "lifecycleLaunch",
  growth: "lifecycleGrowth",
  mature: "lifecycleMature",
  decline: "lifecycleDecline",
};

function normalizePlatform(platform: string | null): "amazon" | "aliexpress" | "shopee" | "ebay" | "walmart" | "other" {
  if (!platform) return "other";
  const lower = platform.toLowerCase();
  if (lower.includes("aliexpress")) return "aliexpress";
  if (lower.includes("shopee")) return "shopee";
  if (lower.includes("ebay")) return "ebay";
  if (lower.includes("walmart")) return "walmart";
  if (lower.includes("amazon")) return "amazon";
  return "other";
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

function StarRating({ rating, t }: { rating: number | null; t: (key: string, values?: Record<string, string | number | Date>) => string }) {
  if (rating == null) return <span className="text-xs text-soft">{t("grid.noRating")}</span>;
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

function ProductCard({ product, t }: { product: ProductOverview; t: (key: string, values?: Record<string, string | number | Date>) => string }) {
  const title = product.name || product.parent_product_id || "";
  const lifecycleKey = lifecycleKeys[product.lifecycle_stage || ""];
  const lifecycle = lifecycleKey ? t(`create.${lifecycleKey}`) : (product.lifecycle_stage || "");
  const badge = getPlatformBadge(product.platform);

  return (
    <div className="group relative flex flex-col overflow-hidden rounded-shell border border-line bg-white/90 shadow-card backdrop-blur transition hover:border-[#f36f8f]/40 hover:shadow-lg">
      <Link
        href={`/products/${product.id}`}
        className="absolute inset-0 z-0"
        aria-label={t("grid.viewDetailAriaLabel", { title })}
      />

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

        {product.session_count > 0 && (
          <span className="absolute right-2 top-2 rounded-pill bg-white/90 px-2.5 py-1 text-[11px] font-semibold text-[#f36f8f] shadow-sm backdrop-blur">
            {t("grid.hasAnalysis")}
          </span>
        )}

        {lifecycle && (
          <span className="absolute bottom-2 left-2 rounded-pill bg-white/90 px-2 py-0.5 text-[10px] font-bold tracking-wide text-ink/70 backdrop-blur">
            {lifecycle}
          </span>
        )}

        {badge && (
          <span className={`absolute top-2 left-2 rounded-pill border px-2 py-0.5 text-[10px] font-bold ${badge.color}`}>
            {badge.label}
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3 className="line-clamp-2 text-sm font-bold leading-5 text-ink group-hover:text-[#f36f8f]">
          {title}
        </h3>

        {product.brand && (
          <p className="text-xs text-soft">{product.brand}</p>
        )}

        <StarRating rating={product.rating} t={t} />

        <div className="mt-auto flex items-center justify-between pt-2 text-xs text-soft">
          <span>{product.review_count} {t("grid.reviewsUnit")}</span>
          <span>{product.variant_count} {t("grid.variantsUnit")}</span>
        </div>

        <div className="relative z-10 mt-2 flex justify-end">
          {product.id != null && (
            <DeleteProductButton productId={product.id} productName={title} />
          )}
        </div>
      </div>
    </div>
  );
}

export function ProductGridWithFilter({ products }: { products: ProductOverview[] }) {
  const t = useTranslations("products");
  const [filter, setFilter] = useState<PlatformFilter>("all");

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

  return (
    <>
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

      {filtered.length > 0 ? (
        <section className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((product) => (
            <ProductCard
              key={`${product.parent_product_id}-${product.id ?? "archived"}`}
              product={product}
              t={t}
            />
          ))}
        </section>
      ) : (
        <p className="text-sm text-soft py-8 text-center">{t("grid.noProductsInPlatform")}</p>
      )}
    </>
  );
}
