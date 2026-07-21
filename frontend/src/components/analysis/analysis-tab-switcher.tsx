"use client";

import React, { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

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
  children: React.ReactNode;
};

export function AnalysisTabSwitcher({ productId, children }: Props) {
  const t = useTranslations("analysis");
  const [activeTab, setActiveTab] = useState<"session" | "parent">("session");
  const [analysisData, setAnalysisData] = useState<ParentAnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (activeTab !== "parent" || analysisData) return;
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
        if (!cancelled) setError(err.message || "Failed to load");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [activeTab, productId, analysisData]);

  const analysis = analysisData?.analysis;

  return (
    <div className="space-y-4">
      {/* Tab switcher */}
      <div className="flex gap-1 rounded-pill border border-line bg-[#f8f6f9] p-1 w-fit">
        <button
          type="button"
          onClick={() => setActiveTab("session")}
          className={`rounded-pill px-4 py-2 text-sm font-semibold transition ${
            activeTab === "session"
              ? "bg-white text-ink shadow-sm"
              : "text-soft hover:text-ink"
          }`}
        >
          {t("tabCurrentUpload")}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("parent")}
          className={`rounded-pill px-4 py-2 text-sm font-semibold transition ${
            activeTab === "parent"
              ? "bg-white text-ink shadow-sm"
              : "text-soft hover:text-ink"
          }`}
        >
          {t("tabParentAnalysis")}
        </button>
      </div>

      {/* Content */}
      {activeTab === "session" ? (
        children
      ) : (
        <section className="rounded-shell border border-line bg-white/90 p-6 shadow-card backdrop-blur">
          {loading ? (
            <p className="text-sm text-soft py-8 text-center">{t("parentAnalysisLoading")}</p>
          ) : error ? (
            <p className="text-sm text-[#b44655] py-8 text-center">{error}</p>
          ) : !analysis?.has_data ? (
            <div className="py-12 text-center">
              <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-[#f5f5f5]">
                <svg className="h-10 w-10 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <p className="mt-4 font-semibold text-ink">{t("parentAnalysisNoData")}</p>
              <p className="mt-1 text-sm text-soft">{t("parentAnalysisNoDataDesc")}</p>
            </div>
          ) : (
            <div>
              {/* Stats cards */}
              <div className="grid gap-4 md:grid-cols-5 mb-6">
                <div className="rounded-card border border-line bg-white/82 px-4 py-4 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                    {t("totalReviews")}
                  </div>
                  <div className="mt-2 font-heading text-3xl font-extrabold text-ink">
                    {analysis.total_reviews}
                  </div>
                </div>
                <div className="rounded-card border border-line bg-white/82 px-4 py-4 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                    {t("positive")}
                  </div>
                  <div className="mt-2 font-heading text-3xl font-extrabold text-[#3d8b74]">
                    {analysis.positive_count}
                  </div>
                </div>
                <div className="rounded-card border border-line bg-white/82 px-4 py-4 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                    {t("negative")}
                  </div>
                  <div className="mt-2 font-heading text-3xl font-extrabold text-[#c45863]">
                    {analysis.negative_count}
                  </div>
                </div>
                <div className="rounded-card border border-line bg-white/82 px-4 py-4 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                    {t("parentAnalysisUnrecognizable")}
                  </div>
                  <div className="mt-2 font-heading text-3xl font-extrabold text-soft">
                    {analysis.unrecognizable_count}
                  </div>
                </div>
                <div className="rounded-card border border-line bg-white/82 px-4 py-4 shadow-sm">
                  <div className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                    {t("parentAnalysisDateRange")}
                  </div>
                  <div className="mt-2 text-sm font-semibold text-ink">
                    {analysis.earliest_date && analysis.latest_date
                      ? `${analysis.earliest_date} ~ ${analysis.latest_date}`
                      : "—"}
                  </div>
                </div>
              </div>

              {/* In-progress indicator */}
              {analysis.in_progress_asin_count > 0 && (
                <div className="flex items-center gap-2 mb-4 text-sm text-[#b08d57]">
                  <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {t("parentAnalysisInProgress", { count: String(analysis.in_progress_asin_count) })}
                </div>
              )}

              {/* Child ASIN list */}
              {analysis.variants.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-soft mb-2">
                    {t("parentAnalysisAsinList", { count: String(analysis.variants.length) })}
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
            </div>
          )}
        </section>
      )}
    </div>
  );
}
