"use client";

import { useMemo, useState } from "react";

import { submitComparisonReport } from "@/lib/api/browser";
import type { ComparisonReportResponse } from "@/lib/api/types";

type CompareReportPanelProps = {
  compareType: string;
  sessionIds: number[];
  productId?: string;
};

export function CompareReportPanel({
  compareType,
  sessionIds,
  productId,
}: CompareReportPanelProps) {
  const [title, setTitle] = useState("");
  const [focusFeature, setFocusFeature] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [report, setReport] = useState<ComparisonReportResponse | null>(null);

  const canSubmit = useMemo(() => sessionIds.length >= 2, [sessionIds.length]);

  async function handleGenerate(): Promise<void> {
    if (!canSubmit) {
      setError("至少需要两个对比对象才能生成报告。");
      return;
    }

    setError("");
    setIsSubmitting(true);
    try {
      const response = await submitComparisonReport({
        compareType,
        sessionIds,
        productId,
        focusFeature: focusFeature.trim() || undefined,
        title: title.trim() || undefined,
      });
      setReport(response);
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "对比报告生成失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            AI REPORT
          </div>
          <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            生成对比报告
          </h3>
          <p className="mt-2 text-sm leading-7 text-soft">
            这一步会显式请求后端生成 AI 对比总结，并把结果落到 `comparison_reports`。
          </p>
        </div>
        <div className="rounded-card border border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
          当前对比对象: {sessionIds.length} 个
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr_auto]">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">报告标题</span>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            placeholder="可选，例如：V1 vs V2 包装优化验证"
          />
        </label>
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">功能点 / 关键词</span>
          <input
            value={focusFeature}
            onChange={(event) => setFocusFeature(event.target.value)}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            placeholder="可选，例如：packaging / installation"
          />
        </label>
        <div className="flex items-end">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!canSubmit || isSubmitting}
            className="inline-flex min-h-12 items-center justify-center rounded-pill bg-ink px-6 py-3 text-sm font-semibold text-white shadow-card transition disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "生成中..." : "生成并保存"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="mt-4 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]">
          {error}
        </div>
      ) : null}

      {report ? (
        <div className="mt-6 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-card border border-line bg-white px-5 py-5">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              报告结果
            </div>
            <div className="mt-3 text-lg font-semibold text-ink">
              #{report.report.id} · {report.report.title || "未命名报告"}
            </div>
            {report.ai_summary?.headline ? (
              <p className="mt-3 text-sm leading-7 text-soft">{report.ai_summary.headline}</p>
            ) : null}
            {report.ai_summary?.summary?.length ? (
              <div className="mt-4 space-y-2 text-sm leading-7 text-ink">
                {report.ai_summary.summary.map((item, index) => (
                  <p key={`summary-${index}`}>- {item}</p>
                ))}
              </div>
            ) : null}
          </div>
          <div className="rounded-card border border-line bg-[#f8fffc] px-5 py-5">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              推荐动作 / 风险提示
            </div>
            <div className="mt-3 space-y-3 text-sm leading-7 text-ink">
              {(report.ai_summary?.recommendations || []).map((item, index) => (
                <p key={`rec-${index}`}>- {item}</p>
              ))}
              {(report.ai_summary?.risks || []).map((item, index) => (
                <p key={`risk-${index}`}>- {item}</p>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="mt-6 rounded-card border border-dashed border-line bg-[#fffafb] px-5 py-5 text-sm leading-7 text-soft">
          生成后会在这里显示报告标题、AI 结论、推荐动作和风险提示。
        </div>
      )}
    </section>
  );
}
