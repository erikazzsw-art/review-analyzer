"use client";

import React, { useEffect, useState } from "react";

type ParentAnalysisData = {
  product: Record<string, unknown>;
  analysis: {
    variants: Array<{ child_asin: string | null; id: number }>;
    total_reviews: number;
    positive_count: number;
    negative_count: number;
    unrecognizable_count: number;
    latest_date: string;
    earliest_date: string;
    in_progress_asin_count: number;
    has_data: boolean;
  };
};

type Props = {
  productId: number;
  variantCount: number;
  children: React.ReactNode;
  labels: {
    tabVariants: string;
    tabAnalysis: string;
    totalReviews: string;
    positive: string;
    negative: string;
    unrecognizable: string;
    dateRange: string;
    inProgress: string;
    noData: string;
    noDataDesc: string;
    loading: string;
    error: string;
  };
};

export function ProductDetailTabs({ productId, variantCount, children, labels }: Props) {
  const [activeTab, setActiveTab] = useState<"variants" | "analysis">("variants");
  const [analysisData, setAnalysisData] = useState<ParentAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (activeTab !== "analysis" || analysisData) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    fetch(`/api/products/${productId}/parent-analysis`, { credentials: "include" })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error((body as { detail?: string }).detail || `HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data: ParentAnalysisData) => {
        if (!cancelled) setAnalysisData(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message || labels.error);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [activeTab, productId, analysisData, labels.error]);

  const analysis = analysisData?.analysis;

  return (
    <div className="rounded-shell border border-line bg-white/90 p-6 shadow-card backdrop-blur">
      {/* Tab 切换 */}
      <div className="flex gap-1 rounded-pill border border-line bg-[#f8f6f9] p-1 w-fit mb-6">
        <button
          type="button"
          onClick={() => setActiveTab("variants")}
          className={`rounded-pill px-4 py-2 text-sm font-semibold transition ${
            activeTab === "variants"
              ? "bg-white text-ink shadow-sm"
              : "text-soft hover:text-ink"
          }`}
        >
          {labels.tabVariants} ({variantCount})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("analysis")}
          className={`rounded-pill px-4 py-2 text-sm font-semibold transition ${
            activeTab === "analysis"
              ? "bg-white text-ink shadow-sm"
              : "text-soft hover:text-ink"
          }`}
        >
          {labels.tabAnalysis}
        </button>
      </div>

      {activeTab === "variants" ? (
        children
      ) : activeTab === "analysis" ? (
        <div>
          {loading ? (
            <p className="text-sm text-soft py-8 text-center">{labels.loading}</p>
          ) : error ? (
            <p className="text-sm text-[#b44655] py-8 text-center">{error}</p>
          ) : !analysis?.has_data ? (
            /* 空状态提示 */
            <div className="py-12 text-center">
              <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-[#f5f5f5]">
                <svg className="h-10 w-10 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <p className="mt-4 font-semibold text-ink">{labels.noData}</p>
              <p className="mt-1 text-sm text-soft">{labels.noDataDesc}</p>
            </div>
          ) : (
            <>
              {/* 统计卡片 */}
              <div className="grid gap-4 md:grid-cols-4 mb-6">
                <div className="rounded-card border border-line bg-white/82 px-4 py-4 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                    {labels.totalReviews}
                  </div>
                  <div className="mt-2 font-heading text-3xl font-extrabold text-ink">
                    {analysis.total_reviews}
                  </div>
                </div>
                <div className="rounded-card border border-line bg-white/82 px-4 py-4 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                    {labels.positive}
                  </div>
                  <div className="mt-2 font-heading text-3xl font-extrabold text-[#3d8b74]">
                    {analysis.positive_count}
                  </div>
                </div>
                <div className="rounded-card border border-line bg-white/82 px-4 py-4 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                    {labels.negative}
                  </div>
                  <div className="mt-2 font-heading text-3xl font-extrabold text-[#c45863]">
                    {analysis.negative_count}
                  </div>
                </div>
                <div className="rounded-card border border-line bg-white/82 px-4 py-4 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                    {labels.unrecognizable}
                  </div>
                  <div className="mt-2 font-heading text-3xl font-extrabold text-soft">
                    {analysis.unrecognizable_count}
                  </div>
                </div>
              </div>

              {/* 时间范围 + 分析中提示 */}
              <div className="flex flex-wrap gap-4 text-sm text-soft">
                {(analysis.earliest_date || analysis.latest_date) && (
                  <span>
                    {labels.dateRange}: {analysis.earliest_date || "—"} ~ {analysis.latest_date || "—"}
                  </span>
                )}
                {analysis.in_progress_asin_count > 0 && (
                  <span className="text-[#b08d57] font-medium">
                    {labels.inProgress.replace("{count}", String(analysis.in_progress_asin_count))}
                  </span>
                )}
              </div>

              {/* 子 ASIN 列表 */}
              {analysis.variants.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-semibold text-soft mb-2">
                    子 ASIN 列表（{analysis.variants.length} 个）
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {analysis.variants.map((v, idx) => (
                      <span
                        key={v.child_asin ?? idx}
                        className="inline-flex rounded-pill bg-[#f3f0f8] px-3 py-1 text-xs font-mono text-ink/70"
                      >
                        {v.child_asin || "—"}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
