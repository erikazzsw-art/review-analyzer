"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Download, FileSpreadsheet, Upload } from "lucide-react";
import { useTranslations } from "next-intl";
import * as XLSX from "xlsx";

import {
  importProducts,
  type ProductImportResponse,
  type ProductImportRowPayload,
} from "@/lib/api/browser";

type ImportColumn = {
  key: keyof ProductImportRowPayload;
  header: string;
  required: boolean;
  aliases: string[];
  example: string | number;
  rule: string;
  kind?: "text" | "number" | "asin" | "bool" | "lifecycle" | "status";
};

function normalizeHeader(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, "");
}

function cleanText(value: unknown): string | undefined {
  const text = String(value ?? "").trim();
  return text || undefined;
}

function cleanNumber(value: unknown): number | undefined {
  const text = String(value ?? "").trim().replace(/,/g, "");
  if (!text) return undefined;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function cleanBool(value: unknown): boolean | undefined {
  const text = String(value ?? "").trim().toLowerCase();
  if (!text) return undefined;
  if (["true", "yes", "y", "1", "是", "fba"].includes(text)) return true;
  if (["false", "no", "n", "0", "否", "fbm"].includes(text)) return false;
  return undefined;
}

function normalizeLifecycle(value: unknown): string | undefined {
  const text = String(value ?? "").trim().toLowerCase();
  if (!text) return undefined;
  const map: Record<string, string> = {
    research: "research",
    "调研期": "research",
    launch: "launch",
    "新品期": "launch",
    growth: "growth",
    "成长期": "growth",
    mature: "mature",
    "成熟期": "mature",
    decline: "decline",
    "衰退期": "decline",
  };
  return map[text] || text;
}

function normalizeStatus(value: unknown): string | undefined {
  const text = String(value ?? "").trim().toLowerCase();
  if (!text) return undefined;
  const map: Record<string, string> = {
    active: "active",
    "在售": "active",
    paused: "paused",
    "暂停": "paused",
    clearance: "clearance",
    "清仓": "clearance",
    retired: "retired",
    "退市": "retired",
  };
  return map[text] || text;
}

function safeSheetName(value: string): string {
  return (value.trim() || "Sheet").slice(0, 31);
}

function safeFilename(value: string): string {
  return value.trim().replace(/[\\/:*?"<>|]+/g, "_") || "product-import-template";
}

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error) return err.message;
  if (err && typeof err === "object" && "message" in err) {
    const message = String((err as { message?: unknown }).message || "").trim();
    if (message) return message;
  }
  return fallback;
}

export function ImportProductsButton() {
  const t = useTranslations("products.import");
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ProductImportResponse | null>(null);
  const [error, setError] = useState("");

  const columns: ImportColumn[] = [
    {
      key: "product_name",
      header: t("columnProductName"),
      required: true,
      aliases: ["产品名称", "父产品名称", "Product Name", "Parent Product"],
      example: "TIDEWE 下水服 WD001",
      rule: t("ruleProductName"),
    },
    {
      key: "child_asin",
      header: t("columnAsin"),
      required: false,
      aliases: ["ASIN", "子ASIN", "子 ASIN", "Child ASIN"],
      example: "B0779NTMYD",
      rule: t("ruleAsin"),
      kind: "asin",
    },
    {
      key: "platform",
      header: t("columnPlatform"),
      required: false,
      aliases: ["平台", "Platform"],
      example: "Amazon",
      rule: t("rulePlatform"),
    },
    {
      key: "category",
      header: t("columnCategory"),
      required: false,
      aliases: ["类目", "品类", "Category"],
      example: "Outdoor",
      rule: t("ruleCategory"),
    },
    {
      key: "lifecycle_stage",
      header: t("columnLifecycle"),
      required: false,
      aliases: ["生命周期", "Lifecycle"],
      example: "growth",
      rule: t("ruleLifecycle"),
      kind: "lifecycle",
    },
    {
      key: "current_version",
      header: t("columnVersion"),
      required: false,
      aliases: ["当前版本", "版本", "Version"],
      example: "V1",
      rule: t("ruleVersion"),
    },
    {
      key: "variant_sku",
      header: t("columnVariantSku"),
      required: false,
      aliases: ["变体SKU", "变体 SKU", "SKU", "Variant SKU"],
      example: "WD001-BLK-M",
      rule: t("ruleVariantSku"),
    },
    {
      key: "variant_name",
      header: t("columnVariantName"),
      required: false,
      aliases: ["变体名称", "变体名", "Variant Name"],
      example: "Black M",
      rule: t("ruleVariantName"),
    },
    {
      key: "color",
      header: t("columnColor"),
      required: false,
      aliases: ["颜色", "Color"],
      example: "Black",
      rule: t("ruleColor"),
    },
    {
      key: "size",
      header: t("columnSize"),
      required: false,
      aliases: ["尺寸", "尺码", "Size"],
      example: "M",
      rule: t("ruleSize"),
    },
    {
      key: "style",
      header: t("columnStyle"),
      required: false,
      aliases: ["款式", "Style"],
      example: "Bootfoot",
      rule: t("ruleStyle"),
    },
    {
      key: "material",
      header: t("columnMaterial"),
      required: false,
      aliases: ["材质", "Material"],
      example: "Neoprene",
      rule: t("ruleMaterial"),
    },
    {
      key: "brand",
      header: t("columnBrand"),
      required: false,
      aliases: ["品牌", "Brand"],
      example: "TIDEWE",
      rule: t("ruleBrand"),
    },
    {
      key: "price",
      header: t("columnPrice"),
      required: false,
      aliases: ["价格", "Price"],
      example: 99.99,
      rule: t("rulePrice"),
      kind: "number",
    },
    {
      key: "price_currency",
      header: t("columnCurrency"),
      required: false,
      aliases: ["币种", "Currency"],
      example: "USD",
      rule: t("ruleCurrency"),
    },
    {
      key: "sales_volume",
      header: t("columnSalesVolume"),
      required: false,
      aliases: ["销量", "Sales Volume"],
      example: 120,
      rule: t("ruleSalesVolume"),
      kind: "number",
    },
    {
      key: "sales_revenue",
      header: t("columnSalesRevenue"),
      required: false,
      aliases: ["销售额", "Sales Revenue"],
      example: 11998.8,
      rule: t("ruleSalesRevenue"),
      kind: "number",
    },
    {
      key: "is_fba",
      header: t("columnFulfillment"),
      required: false,
      aliases: ["配送方式", "FBA", "Fulfillment"],
      example: "FBA",
      rule: t("ruleFulfillment"),
      kind: "bool",
    },
    {
      key: "listing_date",
      header: t("columnListingDate"),
      required: false,
      aliases: ["上架日期", "Listing Date"],
      example: "2026-01-15",
      rule: t("ruleDate"),
    },
    {
      key: "launched_at",
      header: t("columnLaunchedAt"),
      required: false,
      aliases: ["发布日期", "Launch Date"],
      example: "2026-01-10",
      rule: t("ruleDate"),
    },
    {
      key: "status",
      header: t("columnStatus"),
      required: false,
      aliases: ["状态", "Status"],
      example: "active",
      rule: t("ruleStatus"),
      kind: "status",
    },
    {
      key: "image_url",
      header: t("columnImageUrl"),
      required: false,
      aliases: ["图片链接", "Image URL"],
      example: "https://example.com/image.jpg",
      rule: t("ruleImageUrl"),
    },
    {
      key: "core_selling_points",
      header: t("columnSellingPoints"),
      required: false,
      aliases: ["核心卖点", "Selling Points"],
      example: "防水/保暖",
      rule: t("ruleSellingPoints"),
    },
    {
      key: "main_competitors",
      header: t("columnCompetitors"),
      required: false,
      aliases: ["主要竞品", "Competitors"],
      example: "FROGG TOGGS",
      rule: t("ruleCompetitors"),
    },
    {
      key: "owner_role",
      header: t("columnOwnerRole"),
      required: false,
      aliases: ["负责人角色", "Owner Role"],
      example: "产品经理",
      rule: t("ruleOwnerRole"),
    },
    {
      key: "production_cycle_days",
      header: t("columnCycleDays"),
      required: false,
      aliases: ["生产周期天数", "Production Cycle Days"],
      example: 45,
      rule: t("ruleCycleDays"),
      kind: "number",
    },
  ];

  function pickCell(row: Record<string, unknown>, column: ImportColumn): unknown {
    const keys = Object.keys(row);
    const lookup = new Map(keys.map((key) => [normalizeHeader(key), key]));
    const aliases = [column.header, ...column.aliases];
    for (const alias of aliases) {
      const matchedKey = lookup.get(normalizeHeader(alias));
      if (matchedKey) return row[matchedKey];
    }
    return undefined;
  }

  function parseRows(rawRows: Record<string, unknown>[]) {
    const rows: ProductImportRowPayload[] = [];
    const localErrors: Array<{ row: number; detail: string }> = [];

    rawRows.forEach((raw, index) => {
      const parsed: ProductImportRowPayload = { row_number: index + 2 };
      let hasAnyValue = false;

      columns.forEach((column) => {
        const rawValue = pickCell(raw, column);
        if (cleanText(rawValue)) hasAnyValue = true;

        if (column.kind === "number") {
          const numberValue = cleanNumber(rawValue);
          if (numberValue !== undefined) {
            (parsed as Record<string, unknown>)[column.key] = numberValue;
          }
          return;
        }
        if (column.kind === "bool") {
          const boolValue = cleanBool(rawValue);
          if (boolValue !== undefined) {
            (parsed as Record<string, unknown>)[column.key] = boolValue;
          }
          return;
        }
        if (column.kind === "lifecycle") {
          const lifecycle = normalizeLifecycle(rawValue);
          if (lifecycle) parsed.lifecycle_stage = lifecycle;
          return;
        }
        if (column.kind === "status") {
          const status = normalizeStatus(rawValue);
          if (status) parsed.status = status;
          return;
        }
        if (column.kind === "asin") {
          const asin = cleanText(rawValue);
          if (asin) parsed.child_asin = asin.toUpperCase();
          return;
        }

        const text = cleanText(rawValue);
        if (text) {
          (parsed as Record<string, unknown>)[column.key] = text;
        }
      });

      if (!hasAnyValue) return;
      if (!parsed.product_name?.trim()) {
        localErrors.push({ row: index + 2, detail: t("missingProductName") });
        return;
      }
      rows.push(parsed);
    });

    return { rows, localErrors };
  }

  function handleDownloadTemplate() {
    const workbook = XLSX.utils.book_new();
    const headers = columns.map((column) => column.header);
    const exampleRow = columns.map((column) => column.example);
    const importSheet = XLSX.utils.aoa_to_sheet([headers, exampleRow]);
    importSheet["!cols"] = columns.map((column) => ({
      wch: Math.max(14, String(column.header).length + 8),
    }));
    XLSX.utils.book_append_sheet(workbook, importSheet, safeSheetName(t("sheetImport")));

    const instructionRows = [
      [t("instructionField"), t("instructionRequired"), t("instructionRule"), t("instructionExample")],
      ...columns.map((column) => [
        column.header,
        column.required ? t("requiredYes") : t("requiredNo"),
        column.rule,
        column.example,
      ]),
    ];
    const instructionSheet = XLSX.utils.aoa_to_sheet(instructionRows);
    instructionSheet["!cols"] = [{ wch: 24 }, { wch: 12 }, { wch: 68 }, { wch: 28 }];
    XLSX.utils.book_append_sheet(workbook, instructionSheet, safeSheetName(t("sheetInstructions")));

    XLSX.writeFile(workbook, `${safeFilename(t("templateFilename"))}.xlsx`);
  }

  async function handleFileSelected(file: File | undefined) {
    if (!file) return;
    setSubmitting(true);
    setResult(null);
    setError("");

    try {
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: "array" });
      const sheetName = workbook.SheetNames[0];
      if (!sheetName) {
        setError(t("emptyFile"));
        return;
      }

      const worksheet = workbook.Sheets[sheetName];
      const rawRows = XLSX.utils.sheet_to_json<Record<string, unknown>>(worksheet, { defval: "" });
      const parsed = parseRows(rawRows);
      if (parsed.rows.length === 0) {
        setError(parsed.localErrors[0]?.detail || t("emptyFile"));
        return;
      }

      const response = await importProducts(parsed.rows);
      setResult({
        ...response,
        errors: [...parsed.localErrors, ...response.errors],
      });
      router.refresh();
    } catch (err) {
      setError(errorMessage(err, t("importFailed")));
    } finally {
      setSubmitting(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={handleDownloadTemplate}
        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-pill border border-line bg-white px-4 py-3 text-sm font-semibold text-ink shadow-sm transition hover:border-[#f36f8f]/40 hover:bg-[#fff7fa]"
      >
        <Download className="h-4 w-4" />
        {t("downloadTemplate")}
      </button>

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={submitting}
        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-pill border border-line bg-white px-4 py-3 text-sm font-semibold text-ink shadow-sm transition hover:border-[#4a7dc7]/40 hover:bg-[#f7fbff] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? <FileSpreadsheet className="h-4 w-4" /> : <Upload className="h-4 w-4" />}
        {submitting ? t("importing") : t("uploadExcel")}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls,.csv"
        className="hidden"
        onChange={(event) => void handleFileSelected(event.target.files?.[0])}
      />

      {(error || result) && (
        <div className="w-full px-1 py-2 text-sm">
          {error ? (
            <p className="font-semibold text-[#b44655]">{error}</p>
          ) : result ? (
            <div className="space-y-2">
              <p className="font-semibold text-ink">
                {t("summary", {
                  productsCreated: result.products_created,
                  productsUpdated: result.products_updated,
                  variantsCreated: result.variants_created,
                  variantsUpdated: result.variants_updated,
                  variantsSkipped: result.variants_skipped,
                })}
              </p>
              {result.errors.length > 0 && (
                <div className="max-h-28 overflow-auto text-xs leading-6 text-[#b44655]">
                  {result.errors.slice(0, 6).map((item) => (
                    <p key={`${item.row}-${item.detail}`}>
                      {t("rowError", { row: item.row, detail: item.detail })}
                    </p>
                  ))}
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
