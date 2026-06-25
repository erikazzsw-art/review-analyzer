"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { StatCard } from "./stat-card";
import type { TimeRange, PipelineHealth, LlmCosts, JobTrace } from "./types";
import { fetchAnalytics, timeRangeToDays } from "./types";

type Props = { timeRange: TimeRange };

export function OverviewTab({ timeRange }: Props) {
  const [health, setHealth] = useState<PipelineHealth | null>(null);
  const [costs, setCosts] = useState<LlmCosts | null>(null);
  const [failedJobs, setFailedJobs] = useState<JobTrace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const days = timeRangeToDays(timeRange);
    Promise.all([
      fetchAnalytics<PipelineHealth>(`pipeline-health?days=${days}`),
      fetchAnalytics<LlmCosts>(`llm-costs?days=${days}`),
      fetchAnalytics<{ traces: JobTrace[] }>("job-traces?limit=5&offset=0"),
    ])
      .then(([h, c, j]) => {
        setHealth(h);
        setCosts(c);
        setFailedJobs(j.traces.filter((t) => t.status === "failed"));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [timeRange]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl border border-line bg-gray-50" />
          ))}
        </div>
        <div className="h-56 animate-pulse rounded-xl border border-line bg-gray-50" />
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
    <div className="space-y-6">
      {health && costs && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="总调用" value={health.summary.total_calls} />
            <StatCard
              label="错误率"
              value={`${health.summary.error_rate}%`}
              sub={`${health.summary.error_count} 次错误`}
              accent={health.summary.error_rate > 5 ? "danger" : "default"}
            />
            <StatCard
              label="P95 延迟"
              value={`${health.summary.p95_ms}ms`}
              sub={`P99: ${health.summary.p99_ms}ms`}
            />
            <StatCard
              label="总成本"
              value={`¥${costs.summary.total_cost_yuan.toFixed(2)}`}
              sub={`平均 ¥${costs.summary.avg_cost_per_call.toFixed(4)}/次`}
            />
          </div>

          {health.daily.length > 0 && (
            <div className="rounded-xl border border-line bg-white p-4">
              <h3 className="mb-3 text-sm font-medium text-soft">延迟与调用量趋势</h3>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={[...health.daily].reverse()}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="avg_latency_ms"
                      name="平均延迟(ms)"
                      stroke="#8d7be8"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="calls"
                      name="调用数"
                      stroke="#f36f8f"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-line bg-white p-4">
              <h3 className="mb-2 text-sm font-medium text-soft">缓存效率</h3>
              <div className="text-3xl font-bold text-emerald-600">
                {costs.summary.cache_rate.toFixed(1)}%
              </div>
              <div className="mt-1 text-xs text-soft">
                {costs.summary.cache_hits} 次缓存命中 / {costs.summary.total_calls} 总调用
              </div>
            </div>

            <div className="rounded-xl border border-line bg-white p-4">
              <h3 className="mb-2 text-sm font-medium text-soft">最近失败任务</h3>
              {failedJobs.length === 0 ? (
                <div className="text-sm text-soft">暂无失败任务</div>
              ) : (
                <div className="space-y-2">
                  {failedJobs.slice(0, 5).map((job) => (
                    <div key={job.job_id} className="flex items-center justify-between text-xs">
                      <span className="font-mono text-ink">#{job.job_id}</span>
                      <span className="truncate px-2 text-soft">
                        {job.error || "未知错误"}
                      </span>
                      <span className="shrink-0 text-soft">
                        {new Date(job.created_at).toLocaleDateString("zh-CN")}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
