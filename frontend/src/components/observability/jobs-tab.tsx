"use client";

import { Fragment, useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import { JobTraceDetail } from "./job-trace-detail";
import type { JobTrace, JobTracesResponse } from "./types";
import { fetchAnalytics } from "./types";

const PAGE_SIZE = 20;

type StatusFilter = "all" | "completed" | "failed" | "processing";

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "全部" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
  { value: "processing", label: "处理中" },
];

const STATUS_LABELS: Record<string, string> = {
  completed: "已完成",
  failed: "失败",
  processing: "处理中",
  queued: "排队中",
};

const ERROR_TYPE_LABELS: Record<string, string> = {
  insufficient_credits: "Credit 不足",
  timeout: "超时/卡死",
  model_circuit: "模型熔断",
  rate_limit: "限流",
  model_output_invalid: "模型输出异常",
  network: "网络异常",
  database: "数据库异常",
  unknown: "未知错误",
};

export function JobsTab() {
  const [traces, setTraces] = useState<JobTrace[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const statusQuery = statusFilter === "all" ? "" : `&status=${statusFilter}`;
    fetchAnalytics<JobTracesResponse>(`job-traces?limit=${PAGE_SIZE}&offset=${offset}${statusQuery}`)
      .then((res) => {
        setTraces(res.traces);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [offset, statusFilter]);

  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = Math.min(offset + PAGE_SIZE, total);

  function selectStatus(value: StatusFilter) {
    setStatusFilter(value);
    setOffset(0);
    setExpandedId(null);
  }

  async function copyJobId(jobId: number) {
    try {
      await navigator.clipboard.writeText(String(jobId));
      setCopiedId(jobId);
      window.setTimeout(() => setCopiedId((current) => (current === jobId ? null : current)), 1200);
    } catch {
      setCopiedId(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 animate-pulse rounded-lg border border-line bg-gray-50" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-600">
        加载失败: {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1 rounded-lg border border-line bg-gray-50 p-0.5">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => selectStatus(opt.value)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                statusFilter === opt.value
                  ? "bg-white text-ink shadow-sm"
                  : "text-soft hover:text-ink",
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="text-xs text-soft">
          共 {total} 条记录
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-line">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line bg-gray-50">
            <tr>
              <th className="px-4 py-2 font-medium text-soft">Job ID</th>
              <th className="px-4 py-2 font-medium text-soft">状态</th>
              <th className="px-4 py-2 font-medium text-soft">失败定位</th>
              <th className="px-4 py-2 font-medium text-soft">关联</th>
              <th className="px-4 py-2 font-medium text-soft">进度</th>
              <th className="px-4 py-2 font-medium text-soft">LLM</th>
              <th className="px-4 py-2 font-medium text-soft">缓存</th>
              <th className="px-4 py-2 font-medium text-soft">费用</th>
              <th className="px-4 py-2 font-medium text-soft">扣费</th>
              <th className="px-4 py-2 font-medium text-soft">耗时</th>
              <th className="px-4 py-2 font-medium text-soft">时间</th>
            </tr>
          </thead>
          <tbody>
            {traces.map((t) => (
              <Fragment key={t.job_id}>
                <tr
                  className="cursor-pointer border-b border-line transition-colors hover:bg-gray-50"
                  onClick={() => setExpandedId(expandedId === t.job_id ? null : t.job_id)}
                >
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-ink">{t.job_id}</span>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          copyJobId(t.job_id);
                        }}
                        className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-line text-soft transition-colors hover:text-ink"
                        aria-label={`复制 Job ID ${t.job_id}`}
                      >
                        {copiedId === t.job_id ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-2">
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-xs font-medium",
                          t.status === "completed" && "bg-emerald-100 text-emerald-700",
                          t.status === "failed" && "bg-red-100 text-red-700",
                          t.status === "processing" && "bg-yellow-100 text-yellow-700",
                          t.status === "queued" && "bg-gray-100 text-gray-700",
                        )}
                      >
                        {STATUS_LABELS[t.status] || t.status}
                      </span>
                    </td>
                  <td className="px-4 py-2 text-xs">
                    {t.status === "failed" ? (
                      <div className="space-y-0.5">
                        <div className="font-medium text-red-700">{t.failure_stage || "未知阶段"}</div>
                        <div className="text-soft">{t.error_type ? ERROR_TYPE_LABELS[t.error_type] || t.error_type : "-"}</div>
                      </div>
                    ) : (
                      <span className="text-soft">-</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-xs">
                    <div className="max-w-[160px] truncate text-ink" title={t.product_id || ""}>
                      {t.product_id || "-"}
                    </div>
                    <div className="text-soft">session {t.session_id || "-"}</div>
                  </td>
                  <td className="px-4 py-2 text-xs">
                    <div>{t.processed_rows}/{t.total_rows}</div>
                    {t.partial_completed && (
                      <span className="mt-1 inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                        部分完成
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-xs">{t.llm_calls ?? "-"}</td>
                  <td className="px-4 py-2 text-xs">{t.cache_hits ?? "-"}</td>
                  <td className="px-4 py-2 text-xs">
                    {t.total_cost_yuan !== null ? `¥${t.total_cost_yuan.toFixed(4)}` : "-"}
                  </td>
                  <td className="px-4 py-2 text-xs">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 font-medium",
                        t.credit_charged ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600",
                      )}
                    >
                      {t.credit_charged ? "已扣" : "未扣"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-xs">
                    {t.total_duration_ms ? `${(t.total_duration_ms / 1000).toFixed(1)}s` : "-"}
                  </td>
                  <td className="px-4 py-2 text-xs text-soft">
                    {new Date(t.created_at).toLocaleString("zh-CN")}
                  </td>
                </tr>
                {expandedId === t.job_id && (
                  <tr>
                    <td colSpan={11} className="p-0">
                      <JobTraceDetail trace={t} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {traces.length === 0 && (
              <tr>
                <td colSpan={11} className="px-4 py-8 text-center text-sm text-soft">
                  {total === 0 ? (
                    <div className="mx-auto max-w-lg space-y-1 text-left">
                      <div className="font-medium text-ink">暂无任务记录</div>
                      <p className="text-xs leading-5">
                        上传任务来自 upload_jobs。旧环境或新账号可能没有任务；完成一次新的 CSV 上传后再刷新本页。
                      </p>
                    </div>
                  ) : "当前筛选暂无记录"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
          disabled={offset === 0}
          className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-soft transition-colors hover:text-ink disabled:opacity-40"
        >
          上一页
        </button>
        <span className="text-xs text-soft">
          第 {rangeStart}-{rangeEnd} 条
        </span>
        <button
          onClick={() => setOffset(offset + PAGE_SIZE)}
          disabled={offset + PAGE_SIZE >= total}
          className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-soft transition-colors hover:text-ink disabled:opacity-40"
        >
          下一页
        </button>
      </div>
    </div>
  );
}
