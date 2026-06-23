"use client";

import { useState } from "react";

import { submitComparisonReport } from "@/lib/api/browser";
import type { ComparisonReportResponse } from "@/lib/api/types";

type CompareAiSummaryPanelProps = {
  compareType: string;
  sessionIds: number[];
  productId?: string;
};

export function CompareAiSummaryPanel({
  compareType,
  sessionIds,
  productId,
}: CompareAiSummaryPanelProps) {
  const [title, setTitle] = useState("");
  const [focusFeature, setFocusFeature] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [report, setReport] = useState<ComparisonReportResponse | null>(null);
  const canSubmit = sessionIds.length >= 2;

  async function handleGenerate(): Promise<void> {
    if (!canSubmit) {
      setError("AI 总结需要先在筛选器里选出 ≥ 2 个有评论的对比对象。");
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
      setError(candidate.message || "AI 总结生成失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-3 py-1 text-[10px] font-bold tracking-[0.12em] text-[#4a7dc7]">
            可选 · AI 总结
          </div>
          <h3 className="mt-2 font-heading text-lg font-extrabold tracking-[-0.04em] text-ink">
            生成一段 AI 对比总结
          </h3>
          <p className="mt-1 max-w-2xl text-xs text-soft">
            看板已经覆盖了核心指标和差异。如果你需要一段自然语言结论 + 风险提醒 + 推荐动作，可以在这里生成并保存为复盘材料。
          </p>
        </div>
        <div className="rounded-card border border-line bg-[#fffafb] px-3 py-2 text-xs text-soft">
          当前对比对象: {sessionIds.length} 个 session
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_1fr_auto]">
        <label className="space-y-1">
          <span className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">报告标题</span>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="w-full rounded-card border border-line bg-white px-3 py-2 text-sm outline-none focus:border-[#f36f8f]"
            placeholder="可选，例如：V1 vs V2 包装优化验证"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">功能点 / 关键词</span>
          <input
            value={focusFeature}
            onChange={(event) => setFocusFeature(event.target.value)}
            className="w-full rounded-card border border-line bg-white px-3 py-2 text-sm outline-none focus:border-[#f36f8f]"
            placeholder="可选，例如：packaging / installation"
          />
        </label>
        <div className="flex items-end">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!canSubmit || isSubmitting}
            className="inline-flex min-h-10 items-center justify-center rounded-pill bg-ink px-5 py-2 text-sm font-semibold text-white shadow-card disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "生成中..." : "生成 AI 总结"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="mt-3 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-3 py-2 text-xs text-[#b44655]">
          {error}
        </div>
      ) : null}

      {report ? (
        <div className="mt-4 grid gap-3 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-card border border-line bg-white px-4 py-3">
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-soft">报告结果</div>
            <div className="mt-1 text-sm font-semibold text-ink">
              #{report.report.id} · {report.report.title || "未命名报告"}
            </div>
            {report.ai_summary?.headline ? (
              <p className="mt-2 text-sm leading-6 text-soft">{report.ai_summary.headline}</p>
            ) : null}
            {report.ai_summary?.summary?.length ? (
              <div className="mt-3 space-y-1 text-sm leading-6 text-ink">
                {report.ai_summary.summary.map((item, index) => (
                  <p key={`summary-${index}`}>· {item}</p>
                ))}
              </div>
            ) : null}
          </div>
          <div className="rounded-card border border-line bg-[#f8fffc] px-4 py-3">
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-soft">推荐动作 / 风险</div>
            <div className="mt-2 space-y-2 text-sm leading-6 text-ink">
              {(report.ai_summary?.recommendations || []).map((item, index) => (
                <p key={`rec-${index}`}>· {item}</p>
              ))}
              {(report.ai_summary?.risks || []).map((item, index) => (
                <p key={`risk-${index}`}>⚠ {item}</p>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
