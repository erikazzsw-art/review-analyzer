"use client";

import Link from "next/link";
import { useState } from "react";

import {
  downloadCompareExport,
  fetchCompareDataset,
} from "@/lib/api/browser";
import type {
  AnalysisCompareResponse,
  CompareFilterGroup,
  ProductOverview,
} from "@/lib/api/types";

import { CompareAiSummary } from "./compare-ai-summary";
import { CompareDashboard } from "./compare-dashboard";
import { CompareFilterBar, type CompareMode } from "./compare-filter-bar";

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
  const [dataset, setDataset] = useState<AnalysisCompareResponse | null>(initialDataset ?? null);
  const [mode, setMode] = useState<CompareMode>(initialMode ?? "same_product_time");
  const [filterGroups, setFilterGroups] = useState<CompareFilterGroup[]>(initialGroups ?? []);
  const [isFetching, setIsFetching] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState("");

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
      setError(candidate.message || "对比数据加载失败");
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
      setError(candidate.message || "XLSX 导出失败");
    } finally {
      setIsExporting(false);
    }
  }

  const hasDataset = Boolean(dataset && dataset.groups.length > 0);

  return (
    <div className="flex flex-col gap-4">
      {products.length === 0 ? (
        <section className="rounded-shell border border-dashed border-line bg-[#fffafb] px-6 py-8 text-sm text-soft">
          还没有可对比的产品。先去
          <Link href="/upload" className="mx-1 font-semibold text-ink underline">
            上传评论
          </Link>
          完成一次分析后再回来。
        </section>
      ) : (
        <CompareFilterBar
          products={products}
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
              {isExporting ? "导出中..." : "⬇ 下载 XLSX"}
            </button>
          </div>
          <CompareDashboard dataset={dataset} />
          <CompareAiSummary summary={dataset.ai_summary} />
        </>
      ) : products.length > 0 ? (
        <section className="rounded-shell border border-dashed border-line bg-[#fffafb] px-6 py-10 text-sm text-soft">
          选择 2 个或以上对比对象，点击「生成对比」后这里会出现核心指标、问题/亮点差异、风险/机会和推荐动作。
        </section>
      ) : null}
    </div>
  );
}

