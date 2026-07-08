"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  downloadCompareExport,
  fetchCompareDataset,
  fetchProductList,
} from "@/lib/api/browser";
import type {
  AnalysisCompareResponse,
  CompareFilterGroup,
  ProductOverview,
} from "@/lib/api/types";

import { CompareAiSummary } from "./compare-ai-summary";
import { CompareDashboard } from "./compare-dashboard";
import { CompareFilterBar, type CompareMode } from "./compare-filter-bar";
import { CompareHistory } from "./compare-history";

type CompareWorkspaceProps = {
  products: ProductOverview[];
  initialDataset?: AnalysisCompareResponse | null;
  initialMode?: CompareMode;
  initialGroups?: CompareFilterGroup[];
  initialProductId?: string;
};

export function CompareWorkspace({
  products,
  initialDataset,
  initialMode,
  initialGroups,
}: CompareWorkspaceProps) {
  const t = useTranslations("analysis.compare");
  const tCommon = useTranslations("common");
  const [productList, setProductList] = useState<ProductOverview[]>(products);
  const [dataset, setDataset] = useState<AnalysisCompareResponse | null>(initialDataset ?? null);
  const [mode, setMode] = useState<CompareMode>(initialMode ?? "same_product_time");
  const [filterGroups, setFilterGroups] = useState<CompareFilterGroup[]>(initialGroups ?? []);
  const [isFetching, setIsFetching] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchProductList()
      .then((res) => setProductList(res.items))
      .catch(() => {});
  }, []);

  async function handleSubmit(nextMode: CompareMode, groups: CompareFilterGroup[]): Promise<void> {
    setMode(nextMode);
    setFilterGroups(groups);
    setError("");
    setIsFetching(true);
    try {
      const response = await fetchCompareDataset({ compareType: nextMode, groups });
      setDataset(response);
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || t("workspaceLoadFailure"));
      setDataset(null);
    } finally {
      setIsFetching(false);
    }
  }

  async function handleDownload(): Promise<void> {
    if (!filterGroups.length) return;
    setError("");
    setIsExporting(true);
    try {
      await downloadCompareExport({
        compareType: mode,
        groups: filterGroups,
      });
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || t("workspaceExportFailure"));
    } finally {
      setIsExporting(false);
    }
  }

  function handleHistorySelect(
    historyDataset: AnalysisCompareResponse,
    groups: CompareFilterGroup[],
    historyMode: CompareMode,
  ) {
    setDataset(historyDataset);
    setFilterGroups(groups);
    setMode(historyMode);
    setError("");
  }

  const hasDataset = Boolean(dataset && dataset.groups.length > 0);

  return (
    <div className="flex flex-col gap-4">
      {productList.length === 0 ? (
        <section className="rounded-shell border border-dashed border-line bg-[#fffafb] px-6 py-8 text-sm text-soft">
          {t("workspaceNoProductsPrefix")}
          <Link href="/upload" className="mx-1 font-semibold text-ink underline">
            {t("workspaceUploadReviewsLink")}
          </Link>
          {t("workspaceNoProductsSuffix")}
        </section>
      ) : (
        <CompareFilterBar
          products={productList}
          initialMode={mode}
          initialGroups={filterGroups.length > 0 ? filterGroups : undefined}
          isSubmitting={isFetching}
          onSubmit={handleSubmit}
        />
      )}

      {error ? (
        <div className="rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-2 text-sm text-[#b44655]">
          {error}
        </div>
      ) : null}

      {hasDataset && dataset ? (
        <>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              onClick={handleDownload}
              disabled={isExporting}
              className="rounded-pill bg-ink px-5 py-2 text-sm font-semibold text-white shadow-card disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isExporting ? tCommon("exporting") : t("workspaceDownloadXlsx")}
            </button>
          </div>
          <CompareDashboard dataset={dataset} />
          <CompareAiSummary summary={dataset.ai_summary} />
        </>
      ) : productList.length > 0 ? (
        <section className="rounded-shell border border-dashed border-line bg-[#fffafb] px-6 py-10 text-sm text-soft">
          {t("workspaceEmpty")}
        </section>
      ) : null}

      {productList.length > 0 && (
        <CompareHistory onSelect={handleHistorySelect} />
      )}
    </div>
  );
}

