"use client";

import { Download } from "lucide-react";
import { useTranslations } from "next-intl";
import * as XLSX from "xlsx";

import { recordDownload } from "@/lib/api/browser";
import type { ProductVariant } from "@/lib/api/types";

type DownloadVariantsButtonProps = {
  parentProductId: string;
  parentName: string;
  variants: ProductVariant[];
};

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function valueNumber(value: unknown): number | "" {
  if (value === null || value === undefined || value === "") return "";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : "";
}

function safeFilenamePart(value: string): string {
  return value.trim().replace(/[\\/:*?"<>|]+/g, "_").replace(/\s+/g, "_") || "variants";
}

function sheetName(value: string): string {
  const trimmed = value.trim() || "Sheet";
  return trimmed.slice(0, 31);
}

export function DownloadVariantsButton({
  parentProductId,
  parentName,
  variants,
}: DownloadVariantsButtonProps) {
  const t = useTranslations("products.detail");
  const disabled = variants.length === 0;

  function handleDownload() {
    if (disabled) return;

    const headers = [
      t("exportColumnIndex"),
      t("parentProductId"),
      t("exportColumnParentName"),
      t("tableAsin"),
      t("exportColumnVariantSku"),
      t("exportColumnPlatform"),
      t("tableColor"),
      t("tableSize"),
      t("tableStyle"),
      t("tableMaterial"),
      t("tableVariantName"),
      t("tableBrand"),
      t("exportColumnCurrency"),
      t("tablePrice"),
      t("tableReviews"),
      t("tableSales"),
      t("tableRevenue"),
      t("tableFba"),
      t("tableListDate"),
      t("exportColumnLaunchDate"),
      t("exportColumnLatestReviewDate"),
      t("exportColumnStatus"),
      t("exportColumnImageUrl"),
      t("exportColumnCreatedAt"),
    ];

    const rows = variants.map((variant, index) => [
      index + 1,
      parentProductId,
      parentName,
      valueText(variant.child_asin),
      valueText(variant.variant_sku),
      valueText(variant.platform),
      valueText(variant.color),
      valueText(variant.size),
      valueText(variant.style),
      valueText(variant.material),
      valueText(variant.name),
      valueText(variant.brand),
      valueText(variant.price_currency),
      valueNumber(variant.price),
      valueNumber(variant.review_count),
      valueNumber(variant.sales_volume),
      valueNumber(variant.sales_revenue),
      variant.is_fba ? "FBA" : "FBM",
      valueText(variant.listing_date),
      valueText(variant.launched_at),
      valueText(variant.latest_review_date),
      valueText(variant.status),
      valueText(variant.image_url),
      valueText(variant.created_at),
    ]);

    const workbook = XLSX.utils.book_new();
    const variantSheet = XLSX.utils.aoa_to_sheet([headers, ...rows]);
    variantSheet["!cols"] = [
      { wch: 8 },
      { wch: 24 },
      { wch: 24 },
      { wch: 16 },
      { wch: 18 },
      { wch: 12 },
      { wch: 18 },
      { wch: 12 },
      { wch: 12 },
      { wch: 12 },
      { wch: 28 },
      { wch: 18 },
      { wch: 10 },
      { wch: 12 },
      { wch: 12 },
      { wch: 12 },
      { wch: 12 },
      { wch: 10 },
      { wch: 14 },
      { wch: 14 },
      { wch: 16 },
      { wch: 12 },
      { wch: 48 },
      { wch: 20 },
    ];
    XLSX.utils.book_append_sheet(workbook, variantSheet, sheetName(t("exportSheetVariants")));

    const exportedAt = new Date().toISOString();
    const metaSheet = XLSX.utils.aoa_to_sheet([
      [t("exportMetaField"), t("exportMetaValue")],
      [t("parentProductId"), parentProductId],
      [t("exportColumnParentName"), parentName],
      [t("exportMetaVariantCount"), variants.length],
      [t("exportMetaExportedAt"), exportedAt],
    ]);
    metaSheet["!cols"] = [{ wch: 22 }, { wch: 44 }];
    XLSX.utils.book_append_sheet(workbook, metaSheet, sheetName(t("exportSheetInfo")));

    const filename = `${safeFilenamePart(parentName || parentProductId)}-${t("exportFilenameSuffix")}.xlsx`;
    XLSX.writeFile(workbook, filename);
    recordDownload(filename, t("exportDownloadSource"));
  }

  return (
    <button
      type="button"
      onClick={handleDownload}
      disabled={disabled}
      title={disabled ? t("exportVariantsEmpty") : t("exportVariants")}
      className="inline-flex h-9 items-center justify-center gap-2 rounded-pill border border-line bg-white px-3 text-sm font-semibold text-ink shadow-sm transition hover:border-[#f36f8f]/40 hover:bg-[#fff7fa] disabled:cursor-not-allowed disabled:opacity-45"
    >
      <Download className="h-4 w-4" />
      {t("exportVariants")}
    </button>
  );
}
