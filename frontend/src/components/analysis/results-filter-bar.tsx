"use client";

import { useState, useEffect, useTransition } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { Calendar, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ProductSearchCombobox } from "@/components/analysis/product-search-combobox";
import { fetchProductVersions } from "@/lib/api/browser";

type Props = {
  productId: string;
  variantAsin?: string | null;
  range: string;
  start?: string | null;
  end?: string | null;
  timeLabel?: string;
  isAggregated?: boolean;
  version?: string | null;
};

const RANGE_OPTION_KEYS: Array<{ value: string; key: string }> = [
  { value: "default", key: "rangeDefault" },
  { value: "7d", key: "range7d" },
  { value: "14d", key: "range14d" },
  { value: "30d", key: "range30d" },
  { value: "90d", key: "range90d" },
  { value: "all", key: "rangeAll" },
  { value: "custom", key: "rangeCustom" },
];

export function ResultsFilterBar({
  productId,
  variantAsin,
  range,
  start,
  end,
  timeLabel,
  isAggregated,
  version,
}: Props) {
  const t = useTranslations("analysis.filterBar");
  const tCommon = useTranslations("common");
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const [customStart, setCustomStart] = useState<string>(start || "");
  const [customEnd, setCustomEnd] = useState<string>(end || "");
  const [customOpen, setCustomOpen] = useState(false);
  const [versions, setVersions] = useState<Array<{ version: string; review_count: number }>>([]);

  useEffect(() => {
    if (!productId) return;
    fetchProductVersions(productId)
      .then((res) => setVersions(res.items))
      .catch(() => setVersions([]));
  }, [productId]);

  const pushParams = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params.toString());
    Object.entries(patch).forEach(([k, v]) => {
      if (v === null || v === "") next.delete(k);
      else next.set(k, v);
    });
    startTransition(() => {
      router.push(`${pathname}?${next.toString()}`);
    });
  };

  const handleRangeChange = (value: string) => {
    if (value === "custom") {
      setCustomOpen(true);
      return;
    }
    pushParams({
      range: value,
      start: null,
      end: null,
      session_id: value === "default" ? params.get("session_id") : null,
    });
  };

  const handleProductChange = (pid: string, options?: { variantAsin?: string | null }) => {
    const nextVariantAsin = options?.variantAsin || null;
    if (!pid || (pid === productId && (variantAsin || null) === nextVariantAsin)) return;
    pushParams({
      product_id: pid,
      variant_asin: nextVariantAsin,
      session_id: null,
      range: "default",
      start: null,
      end: null,
      version: null,
    });
  };

  const handleVersionChange = (value: string) => {
    pushParams({
      version: value === "__all__" ? null : value,
      session_id: null,
    });
  };

  const handleCustomApply = () => {
    if (!customStart || !customEnd) return;
    if (customStart > customEnd) return;
    setCustomOpen(false);
    pushParams({
      range: "custom",
      start: customStart,
      end: customEnd,
      session_id: null,
    });
  };

  return (
    <div className="sticky top-0 z-30 -mx-4 flex flex-wrap items-center gap-3 border-b border-line bg-white/95 px-4 py-3 backdrop-blur lg:-mx-6 lg:px-6">
      <div className="flex flex-1 flex-wrap items-center gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-soft">
            {t("product")}
          </span>
          <ProductSearchCombobox
            value={productId}
            variantAsin={variantAsin}
            onChange={handleProductChange}
          />
        </div>

        {versions.length > 1 && (
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-soft">
              {t("version")}
            </span>
            <Select value={version || "__all__"} onValueChange={handleVersionChange}>
              <SelectTrigger className="h-9 w-32 rounded-pill border-line bg-white text-sm font-medium">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">{t("allVersions")}</SelectItem>
                {versions.map((v) => (
                  <SelectItem key={v.version} value={v.version}>
                    {v.version} ({v.review_count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-soft">
            {t("timeRange")}
          </span>
          <div className="relative flex items-center gap-2">
            <Select value={range} onValueChange={handleRangeChange}>
              <SelectTrigger className="h-9 w-44 rounded-pill border-line bg-white text-sm font-medium">
                <Calendar className="mr-1 h-3.5 w-3.5 text-soft" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RANGE_OPTION_KEYS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {t(opt.key)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {(range === "custom" || customOpen) && (
              <div className="absolute right-0 top-full z-50 mt-1 flex flex-col gap-2 rounded-card border border-line bg-white p-3 shadow-card">
                <div className="flex items-center gap-2">
                  <input
                    type="date"
                    value={customStart}
                    onChange={(e) => setCustomStart(e.target.value)}
                    className="h-9 rounded-md border border-line bg-white px-2 text-sm"
                  />
                  <span className="text-xs text-soft">{t("dateSep")}</span>
                  <input
                    type="date"
                    value={customEnd}
                    onChange={(e) => setCustomEnd(e.target.value)}
                    className="h-9 rounded-md border border-line bg-white px-2 text-sm"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setCustomOpen(false)}
                    className="rounded-pill border border-line bg-white px-3 py-1.5 text-xs text-soft"
                  >
                    {tCommon("cancel")}
                  </button>
                  <button
                    type="button"
                    onClick={handleCustomApply}
                    disabled={!customStart || !customEnd || customStart > customEnd}
                    className="rounded-pill bg-ink px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                  >
                    {tCommon("apply")}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {timeLabel && (
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-soft">
              {t("currentView")}
            </span>
            <div className="flex h-9 items-center gap-2 rounded-pill bg-[#faf8fb] px-3 text-xs font-medium text-soft">
              <span>{timeLabel}</span>
              {isAggregated && (
                <span className="rounded-pill bg-rose/15 px-1.5 py-0.5 text-[10px] font-semibold text-rose">
                  {t("aggregatedBadge")}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {isPending && (
        <div className="flex items-center gap-1.5 text-xs text-soft">
          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
          {tCommon("reloading")}
        </div>
      )}
    </div>
  );
}
