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
import { EmptyDataNotice } from "./empty-data-notice";
import {
  getCostStatus,
  getErrorRateStatus,
  getP95LatencyStatus,
  statusToAccent,
} from "./metric-status";
import type { TimeRange, PipelineHealth, LlmCosts, JobTrace, JobTracesResponse } from "./types";
import {
  fetchAnalytics,
  formatBucketLabel,
  formatTimeRangeLabel,
  timeRangeToAnalyticsQuery,
  timeRangeUsesHourlyBuckets,
} from "./types";

type Props = { timeRange: TimeRange };

export function OverviewTab({ timeRange }: Props) {
  const [health, setHealth] = useState<PipelineHealth | null>(null);
  const [costs, setCosts] = useState<LlmCosts | null>(null);
  const [failedJobs, setFailedJobs] = useState<JobTrace[]>([]);
  const [traceTotal, setTraceTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const rangeQuery = timeRangeToAnalyticsQuery(timeRange);
    Promise.all([
      fetchAnalytics<PipelineHealth>(`pipeline-health?${rangeQuery}`),
      fetchAnalytics<LlmCosts>(`llm-costs?${rangeQuery}`),
      fetchAnalytics<JobTracesResponse>("job-traces?limit=5&offset=0"),
    ])
      .then(([h, c, j]) => {
        setHealth(h);
        setCosts(c);
        setFailedJobs(j.traces.filter((t) => t.status === "failed"));
        setTraceTotal(j.total);
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

  if (!health || !costs) return null;

  const errorStatus = getErrorRateStatus(health.summary.error_rate);
  const p95Status = getP95LatencyStatus(health.summary.p95_ms);
  const costStatus = getCostStatus(costs.summary.total_cost_yuan, timeRange);
  const hasLlmEvents = health.summary.total_calls > 0 || health.daily.length > 0;
  const hasUsageLog = costs.summary.total_calls > 0 || costs.daily.length > 0;
  const trendUnit = timeRangeUsesHourlyBuckets(timeRange) ? "小时" : "每日";
  const rangeLabel = formatTimeRangeLabel(timeRange);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          label="总调用"
          value={health.summary.total_calls}
          description={`${rangeLabel}内实际发起的 LLM 调用次数，用来判断系统是否真的在处理分析任务。`}
          normalRange="与上传量同向变化；突然归零通常代表没有新任务或埋点未写入。"
          actionHint="先看任务 Tab 是否有新 trace，再确认 analytics_events 是否有 llm_call。"
        />
        <StatCard
          label="错误率"
          value={`${health.summary.error_rate}%`}
          sub={`${health.summary.error_count} 次错误`}
          accent={statusToAccent(errorStatus)}
          status={errorStatus}
          description="LLM 调用失败占比，反映模型接口、网络、配额或返回格式是否稳定。"
          normalRange="< 5%；5%-10% 注意，10%-20% 异常，≥ 20% 严重。"
          actionHint="查看任务 Tab 的失败任务和 trace 阶段，再看模型状态是否熔断。"
        />
        <StatCard
          label="P95 延迟"
          value={`${health.summary.p95_ms}ms`}
          sub={`P99: ${health.summary.p99_ms}ms`}
          accent={statusToAccent(p95Status)}
          status={p95Status}
          description="95% 的 LLM 调用会在这个时间内完成，比平均值更能反映慢请求体验。"
          normalRange="< 15s；15-20s 注意，20-30s 异常，≥ 30s 严重。"
          actionHint="查看趋势图是否突然升高，再切到任务 Tab 定位最慢阶段。"
        />
        <StatCard
          label="总成本"
          value={`¥${costs.summary.total_cost_yuan.toFixed(2)}`}
          sub={`平均 ¥${costs.summary.avg_cost_per_call.toFixed(4)}/次`}
          accent={statusToAccent(costStatus)}
          status={costStatus}
          description={`${rangeLabel}内记录到 llm_usage_log 的模型费用。状态按当前窗口折算为日花费判断。`}
          normalRange="折算日花费 < ¥5；¥5-10 注意，¥10-20 异常，≥ ¥20 严重。"
          actionHint="切到成本 Tab 看具体模型和 token 消耗，确认是否有异常批量任务。"
        />
      </div>

      {!hasLlmEvents && (
        <EmptyDataNotice
          title="暂无 LLM 调用事件"
          description="概览的错误率和延迟来自 analytics_events 里的 llm_call 事件；没有数据通常是所选时间范围内没有分析任务、任务还未触发 LLM，或埋点尚未写入。"
          action="切到 24小时/7天确认历史数据，或完成一次新上传后检查 worker 是否写入 analytics_events。"
        />
      )}

      {!hasUsageLog && (
        <EmptyDataNotice
          title="暂无 LLM 用量日志"
          description="成本来自 llm_usage_log；没有数据通常表示所选时间范围内没有实际计费调用，或用量记录还没有接到分析链路。"
          action="完成一次需要 LLM 的分析任务，再到成本 Tab 确认模型、token 和费用是否出现。"
        />
      )}

      {health.daily.length > 0 && (
        <div className="rounded-xl border border-line bg-white p-4">
          <h3 className="mb-3 text-sm font-medium text-soft">{trendUnit}延迟与调用量趋势</h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={[...health.daily].reverse()}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(value) => formatBucketLabel(String(value), timeRange)}
                />
                <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                <Tooltip labelFormatter={(value) => formatBucketLabel(String(value), timeRange)} />
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
        <StatCard
          label="缓存命中率"
          value={`${costs.summary.cache_rate.toFixed(1)}%`}
          sub={`${costs.summary.cache_hits} 次缓存命中 / ${costs.summary.total_calls} 总调用`}
          accent={costs.summary.cache_rate >= 50 ? "success" : "default"}
          description="已有结果被复用的比例。命中越高，说明重复评论或相似评论越多，费用和等待时间会下降。"
          normalRange="重复上传或同品类批次通常应逐步接近 50% 以上；首次上传偏低是正常现象。"
          actionHint="切到缓存 Tab 看节省率趋势；若重复上传仍偏低，再检查缓存写入和相似度策略。"
        />

        <div className="rounded-xl border border-line bg-white p-4">
          <h3 className="mb-2 text-sm font-medium text-soft">最近失败任务</h3>
          {traceTotal === 0 ? (
            <div className="space-y-1 text-sm text-soft">
              <div>暂无 trace 数据</div>
              <p className="text-xs">
                Trace 只记录启用结构化追踪后的上传任务；老任务或尚未进入处理阶段的任务可能没有。
                下一步可切到任务 Tab，完成一次新上传后查看 trace 是否生成。
              </p>
            </div>
          ) : failedJobs.length === 0 ? (
            <div className="space-y-1 text-sm text-soft">
              <div>暂无失败任务</div>
              <p className="text-xs">当前可见 trace 都没有失败；如错误率异常，请切到任务 Tab 查看更早分页。</p>
            </div>
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
    </div>
  );
}
