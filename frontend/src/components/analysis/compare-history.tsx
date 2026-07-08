"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import {
  deleteCompareHistory,
  fetchCompareHistory,
  fetchCompareHistoryEntry,
} from "@/lib/api/browser";
import type {
  AnalysisCompareResponse,
  CompareFilterGroup,
  CompareHistoryItem,
} from "@/lib/api/types";

import type { CompareMode } from "./compare-filter-bar";

type CompareHistoryProps = {
  onSelect: (
    dataset: AnalysisCompareResponse,
    groups: CompareFilterGroup[],
    mode: CompareMode,
  ) => void;
};

const MODE_KEY_MAP: Record<string, string> = {
  same_product_time: "modeTime",
  same_product_version: "modeVersion",
  multi_product: "modeMulti",
  custom: "modeCustom",
};

export function CompareHistory({ onSelect }: CompareHistoryProps) {
  const t = useTranslations("analysis.compare");
  const tCommon = useTranslations("common");
  const [items, setItems] = useState<CompareHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loadingFingerprint, setLoadingFingerprint] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadHistory = useCallback(async (q?: string) => {
    setIsLoading(true);
    try {
      const result = await fetchCompareHistory(q || undefined, 20, 0);
      setItems(result.items);
      setTotal(result.total);
    } catch {
      // silently fail
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  function handleSearchChange(value: string) {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      loadHistory(value);
    }, 300);
  }

  async function handleSelect(item: CompareHistoryItem) {
    setLoadingFingerprint(item.fingerprint);
    try {
      const entry = await fetchCompareHistoryEntry(item.fingerprint);
      const rawGroups = entry.filter_groups as Array<Record<string, unknown>>;
      const groups: CompareFilterGroup[] = rawGroups.map((g) => ({
        productId: (g.productId ?? g.product_id ?? "") as string,
        versions: (g.versions ?? []) as string[],
        dateStart: (g.dateStart ?? g.date_start ?? undefined) as string | undefined,
        dateEnd: (g.dateEnd ?? g.date_end ?? undefined) as string | undefined,
      }));
      onSelect(
        entry.dataset,
        groups,
        entry.compare_type as CompareMode,
      );
    } catch {
      // silently fail
    } finally {
      setLoadingFingerprint(null);
    }
  }

  async function handleDelete(fingerprint: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm(t("historyDeleteConfirm"))) return;
    try {
      await deleteCompareHistory(fingerprint);
      setItems((prev) => prev.filter((i) => i.fingerprint !== fingerprint));
      setTotal((prev) => Math.max(0, prev - 1));
    } catch {
      // silently fail
    }
  }

  return (
    <section className="rounded-shell border border-line bg-white px-6 py-5 shadow-card">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-heading text-base font-bold tracking-tight text-ink">
          {t("historyTitle")}
          {total > 0 && (
            <span className="ml-2 text-xs font-normal text-soft">({total})</span>
          )}
        </h3>
        <input
          type="text"
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder={t("historySearchPlaceholder")}
          className="h-8 w-56 rounded-md border border-line bg-white px-3 text-sm text-ink placeholder:text-soft/60 focus:border-ink focus:outline-none"
        />
      </div>

      {isLoading && items.length === 0 ? (
        <p className="py-4 text-center text-sm text-soft">{tCommon("loading")}</p>
      ) : items.length === 0 ? (
        <p className="py-4 text-center text-sm text-soft">
          {t("historyEmpty")}
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {items.map((item) => (
            <li
              key={item.fingerprint}
              onClick={() => handleSelect(item)}
              className="group flex cursor-pointer items-center gap-3 px-2 py-3 transition-colors hover:bg-[#fafafa]"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="inline-flex rounded-full bg-[#f0f0f0] px-2 py-0.5 text-[11px] font-medium text-soft">
                    {MODE_KEY_MAP[item.compare_type]
                      ? t(MODE_KEY_MAP[item.compare_type])
                      : item.compare_type}
                  </span>
                  <span className="truncate text-sm font-medium text-ink">
                    {item.product_names.length > 0
                      ? item.product_names.join(" vs ")
                      : t("historyUnknownProduct")}
                  </span>
                </div>
                {item.group_labels.length > 0 && (
                  <p className="mt-0.5 truncate text-xs text-soft">
                    {item.group_labels.join(" | ")}
                  </p>
                )}
              </div>
              <time className="shrink-0 text-xs text-soft">
                {new Date(item.created_at).toLocaleDateString("zh-CN")}
              </time>
              {loadingFingerprint === item.fingerprint ? (
                <span className="shrink-0 text-xs text-soft">{tCommon("loading")}</span>
              ) : (
                <button
                  type="button"
                  onClick={(e) => handleDelete(item.fingerprint, e)}
                  className="shrink-0 rounded p-1 text-soft opacity-0 transition-opacity hover:bg-[#fee] hover:text-[#c44] group-hover:opacity-100"
                  title={tCommon("delete")}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14" />
                  </svg>
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
