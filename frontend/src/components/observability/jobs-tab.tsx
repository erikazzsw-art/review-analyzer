"use client";

import { useEffect, useState } from "react";
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

export function JobsTab() {
  const [traces, setTraces] = useState<JobTrace[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchAnalytics<JobTracesResponse>(`job-traces?limit=${PAGE_SIZE}&offset=${offset}`)
      .then((res) => {
        setTraces(res.traces);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [offset]);

  const filtered = statusFilter === "all"
    ? traces
    : traces.filter((t) => t.status === statusFilter);
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = Math.min(offset + PAGE_SIZE, total);

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
              onClick={() => setStatusFilter(opt.value)}
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
              <th className="px-4 py-2 font-medium text-soft">耗时</th>
              <th className="px-4 py-2 font-medium text-soft">LLM</th>
              <th className="px-4 py-2 font-medium text-soft">缓存</th>
              <th className="px-4 py-2 font-medium text-soft">费用</th>
              <th className="px-4 py-2 font-medium text-soft">时间</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr key={t.job_id} className="group">
                <td colSpan={7} className="p-0">
                  <div
                    className="flex cursor-pointer items-center border-b border-line px-4 py-2 transition-colors hover:bg-gray-50"
                    onClick={() => setExpandedId(expandedId === t.job_id ? null : t.job_id)}
                  >
                    <div className="w-[80px] font-mono text-xs">{t.job_id}</div>
                    <div className="w-[80px]">
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-xs font-medium",
                          t.status === "completed" && "bg-emerald-100 text-emerald-700",
                          t.status === "failed" && "bg-red-100 text-red-700",
                          t.status === "processing" && "bg-yellow-100 text-yellow-700",
                          t.status === "queued" && "bg-gray-100 text-gray-700",
                        )}
                      >
                        {t.status}
                      </span>
                    </div>
                    <div className="w-[80px] text-xs">
                      {t.total_duration_ms ? `${(t.total_duration_ms / 1000).toFixed(1)}s` : "-"}
                    </div>
                    <div className="w-[60px] text-xs">{t.llm_calls ?? "-"}</div>
                    <div className="w-[60px] text-xs">{t.cache_hits ?? "-"}</div>
                    <div className="w-[80px] text-xs">
                      {t.total_cost_yuan ? `¥${t.total_cost_yuan.toFixed(4)}` : "-"}
                    </div>
                    <div className="flex-1 text-xs text-soft">
                      {new Date(t.created_at).toLocaleString("zh-CN")}
                    </div>
                  </div>
                  {expandedId === t.job_id && <JobTraceDetail trace={t} />}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-sm text-soft">
                  {total === 0 ? (
                    <div className="mx-auto max-w-lg space-y-1 text-left">
                      <div className="font-medium text-ink">暂无 trace 数据</div>
                      <p className="text-xs leading-5">
                        任务 trace 来自 upload_jobs.trace_json，只会记录启用结构化追踪后的上传任务。
                        旧任务、还未进入处理阶段的任务，或 trace 写入失败的任务不会出现在这里。
                      </p>
                      <p className="text-xs font-medium">
                        下一步：完成一次新的 CSV 上传并等待任务结束，再刷新本页；若仍为空，检查 worker 是否持久化 trace_json。
                      </p>
                    </div>
                  ) : (
                    "当前筛选暂无记录"
                  )}
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
