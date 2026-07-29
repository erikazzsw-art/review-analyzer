"use client";

import { useEffect, useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { StatCard } from "./stat-card";
import { EmptyDataNotice } from "./empty-data-notice";
import { getCostStatus, statusToAccent } from "./metric-status";
import type { TimeRange, LlmCosts } from "./types";
import {
  fetchAnalytics,
  formatBucketLabel,
  formatTimeRangeLabel,
  timeRangeToAnalyticsQuery,
  timeRangeUsesHourlyBuckets,
} from "./types";

const MODEL_COLORS: Record<string, string> = {
  "deepseek-chat": "#8d7be8",
  "gpt-4o-mini": "#f36f8f",
  "qwen-plus": "#47c9af",
};

function getModelColor(model: string): string {
  return MODEL_COLORS[model] || "#94a3b8";
}

function formatJobDate(value: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value.slice(0, 10);
  return parsed.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

function formatModelCounts(modelCounts: Record<string, number>): string {
  const entries = Object.entries(modelCounts);
  if (entries.length === 0) return "-";
  return entries
    .map(([model, count]) => `${model}×${count}`)
    .join(" / ");
}

const TOKEN_SEVERITY_STYLES: Record<string, string> = {
  normal: "text-soft",
  warning: "text-amber-600",
  critical: "text-red-600",
};

type Props = { timeRange: TimeRange };

export function CostTab({ timeRange }: Props) {
  const [data, setData] = useState<LlmCosts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchAnalytics<LlmCosts>(`llm-costs?${timeRangeToAnalyticsQuery(timeRange)}`)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [timeRange]);

  const { chartData, models, modelSummary } = useMemo(() => {
    if (!data) return { chartData: [], models: [], modelSummary: [] };

    const dateMap: Record<string, Record<string, number>> = {};
    const modelSet = new Set<string>();
    const summaryMap: Record<string, { calls: number; tokens_in: number; tokens_out: number; cost: number; cache_hits: number }> = {};

    for (const row of data.daily) {
      modelSet.add(row.model);
      if (!dateMap[row.date]) dateMap[row.date] = {};
      dateMap[row.date][row.model] = (dateMap[row.date][row.model] || 0) + row.cost_yuan;

      if (!summaryMap[row.model]) {
        summaryMap[row.model] = { calls: 0, tokens_in: 0, tokens_out: 0, cost: 0, cache_hits: 0 };
      }
      summaryMap[row.model].calls += row.calls;
      summaryMap[row.model].tokens_in += row.tokens_in;
      summaryMap[row.model].tokens_out += row.tokens_out;
      summaryMap[row.model].cost += row.cost_yuan;
      summaryMap[row.model].cache_hits += row.cache_hits;
    }

    const allModels = Array.from(modelSet);
    const chart = Object.entries(dateMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, costs]) => ({ date, ...costs }));

    const summary = allModels.map((model) => ({
      model,
      ...summaryMap[model],
    }));

    return { chartData: chart, models: allModels, modelSummary: summary };
  }, [data]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-xl border border-line bg-gray-50" />
          ))}
        </div>
        <div className="h-64 animate-pulse rounded-xl border border-line bg-gray-50" />
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

  if (!data) return null;

  const costStatus = getCostStatus(data.summary.total_cost_yuan, timeRange);
  const hasUsageLog = data.summary.total_calls > 0 || data.daily.length > 0;
  const hasCostAttribution = data.job_rankings.length > 0 || data.token_anomalies.length > 0;
  const bucketLabel = timeRangeUsesHourlyBuckets(timeRange) ? "小时" : "每日";
  const rangeLabel = formatTimeRangeLabel(timeRange);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <StatCard
          label="总费用"
          value={`¥${data.summary.total_cost_yuan.toFixed(2)}`}
          accent={statusToAccent(costStatus)}
          status={costStatus}
          description={`${rangeLabel}内记录到 llm_usage_log 的模型费用。状态按当前窗口折算为日花费判断。`}
          normalRange="折算日花费 < ¥5；¥5-10 注意，¥10-20 异常，≥ ¥20 严重。"
          actionHint="看下方模型汇总，优先检查费用最高的模型和异常 token 增长。"
        />
        <StatCard
          label="单评论成本"
          value={`¥${data.summary.avg_cost_per_review.toFixed(4)}`}
          sub={`${data.summary.trace_review_count.toLocaleString()} 条 trace 评论`}
          description="按任务 trace 汇总的平均每条评论成本，用来判断单批上传是否变贵。"
          normalRange="应随模型和 prompt 保持相对稳定；突然升高通常来自模型切换、token 变长或缓存下降。"
          actionHint="看单任务成本排行和 token 异常排行，优先定位最贵 job。"
        />
        <StatCard
          label="总调用"
          value={data.summary.total_calls}
          description="所选时间内进入 LLM 用量日志的调用次数。它用于判断成本变化是否由调用量增加造成。"
          normalRange="应与上传量和待分析评论量大体同向变化。"
          actionHint="调用数突然升高时，切到任务 Tab 查看是否有重复上传或异常批处理。"
        />
        <StatCard
          label="缓存命中率"
          value={`${data.summary.cache_rate.toFixed(1)}%`}
          sub={`${data.summary.cache_hits} 次命中`}
          accent={data.summary.cache_rate >= 50 ? "success" : "default"}
          description="命中缓存的调用占比。命中后通常不再产生模型费用，因此这个值越高越省钱。"
          normalRange="重复上传或同品类任务通常应逐步接近 50% 以上；首次上传偏低是正常现象。"
          actionHint="切到缓存 Tab 查看节省率；如果重复任务仍偏低，检查缓存写入和相似评论复用。"
        />
        <StatCard
          label="平均单次成本"
          value={`¥${data.summary.avg_cost_per_call.toFixed(4)}`}
          description="平均每次未命中缓存的 LLM 调用费用，用来发现 prompt 变长或模型切换导致的单次成本上升。"
          normalRange="应随模型和 prompt 版本保持相对稳定。"
          actionHint="查看模型汇总里的输入/输出 tokens，定位是否有某个模型或批次异常。"
        />
      </div>

      {!hasUsageLog && (
        <EmptyDataNotice
          title="暂无 LLM 用量日志"
          description="成本页只统计 llm_usage_log；没有数据通常是当前时间范围没有实际模型调用、调用全部未写日志，或刚完成任务但日志还未刷新。"
          action="切换到 7天/30天，或完成一次需要 LLM 的分析任务后再刷新本页。"
        />
      )}

      {hasUsageLog && !hasCostAttribution && (
        <EmptyDataNotice
          title="暂无任务级成本归因"
          description="任务成本排行依赖新版 upload_jobs.trace_json；老任务或尚未完成 trace 持久化的任务可能只有 llm_usage_log 汇总。"
          action="完成一次新上传后刷新，或切到任务 Tab 查看 trace 是否包含 total_cost_yuan。"
        />
      )}

      {chartData.length > 0 && (
        <div className="rounded-xl border border-line bg-white p-4">
          <h3 className="mb-3 text-sm font-medium text-soft">{bucketLabel}成本 (按模型)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(value) => formatBucketLabel(String(value), timeRange)}
                />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `¥${v}`} />
                <Tooltip
                  formatter={(v) => `¥${Number(v).toFixed(4)}`}
                  labelFormatter={(value) => formatBucketLabel(String(value), timeRange)}
                />
                <Legend />
                {models.map((model) => (
                  <Bar
                    key={model}
                    dataKey={model}
                    name={model}
                    stackId="cost"
                    fill={getModelColor(model)}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {(data.job_rankings.length > 0 || data.token_anomalies.length > 0) && (
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="overflow-x-auto rounded-xl border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h3 className="text-sm font-medium text-soft">单任务成本排行</h3>
            </div>
            <table className="w-full text-left text-xs">
              <thead className="border-b border-line bg-gray-50">
                <tr>
                  <th className="px-4 py-2 font-medium text-soft">Job</th>
                  <th className="px-4 py-2 font-medium text-soft">评论</th>
                  <th className="px-4 py-2 font-medium text-soft">LLM / 缓存</th>
                  <th className="px-4 py-2 font-medium text-soft">模型</th>
                  <th className="px-4 py-2 font-medium text-soft">费用</th>
                  <th className="px-4 py-2 font-medium text-soft">单评论</th>
                </tr>
              </thead>
              <tbody>
                {data.job_rankings.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-soft">
                      暂无任务成本排行
                    </td>
                  </tr>
                ) : (
                  data.job_rankings.slice(0, 8).map((job) => (
                    <tr key={job.job_id} className="border-b border-line last:border-0">
                      <td className="px-4 py-2 font-mono text-ink">#{job.job_id}</td>
                      <td className="px-4 py-2">{job.review_count.toLocaleString()}</td>
                      <td className="px-4 py-2">{job.llm_calls} / {job.cache_hits}</td>
                      <td className="max-w-[180px] truncate px-4 py-2" title={formatModelCounts(job.model_counts)}>
                        {job.dominant_model || "-"}
                      </td>
                      <td className="px-4 py-2 font-medium">¥{job.total_cost_yuan.toFixed(4)}</td>
                      <td className="px-4 py-2">¥{job.cost_per_review_yuan.toFixed(4)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="overflow-x-auto rounded-xl border border-line bg-white">
            <div className="border-b border-line px-4 py-3">
              <h3 className="text-sm font-medium text-soft">Token 异常排行</h3>
            </div>
            <table className="w-full text-left text-xs">
              <thead className="border-b border-line bg-gray-50">
                <tr>
                  <th className="px-4 py-2 font-medium text-soft">来源</th>
                  <th className="px-4 py-2 font-medium text-soft">模型</th>
                  <th className="px-4 py-2 font-medium text-soft">Tokens</th>
                  <th className="px-4 py-2 font-medium text-soft">费用</th>
                  <th className="px-4 py-2 font-medium text-soft">状态</th>
                </tr>
              </thead>
              <tbody>
                {data.token_anomalies.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-soft">
                      暂无 token 异常排行
                    </td>
                  </tr>
                ) : (
                  data.token_anomalies.slice(0, 8).map((row) => (
                    <tr key={row.usage_id} className="border-b border-line last:border-0">
                      <td className="px-4 py-2 font-mono text-ink">
                        {row.job_id ? `#${row.job_id}` : `u${row.usage_id}`}
                      </td>
                      <td className="px-4 py-2">{row.model}</td>
                      <td className="px-4 py-2">{row.total_tokens.toLocaleString()}</td>
                      <td className="px-4 py-2">¥{row.cost_yuan.toFixed(4)}</td>
                      <td className={`px-4 py-2 font-medium ${TOKEN_SEVERITY_STYLES[row.severity]}`}>
                        {row.severity === "critical" ? "严重" : row.severity === "warning" ? "注意" : "正常"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {(data.model_switches.length > 0 || data.model_switch_jobs.length > 0) && (
        <div className="overflow-x-auto rounded-xl border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h3 className="text-sm font-medium text-soft">模型切换导致的成本变化</h3>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="border-b border-line bg-gray-50">
              <tr>
                <th className="px-4 py-2 font-medium text-soft">时间</th>
                <th className="px-4 py-2 font-medium text-soft">主导模型变化</th>
                <th className="px-4 py-2 font-medium text-soft">窗口费用变化</th>
                <th className="px-4 py-2 font-medium text-soft">新模型增量</th>
              </tr>
            </thead>
            <tbody>
              {data.model_switches.slice(0, 8).map((row) => (
                <tr key={`${row.previous_date}-${row.date}`} className="border-b border-line last:border-0">
                  <td className="px-4 py-2">{formatBucketLabel(row.date, timeRange)}</td>
                  <td className="px-4 py-2">
                    {row.previous_dominant_model} → {row.current_dominant_model}
                  </td>
                  <td className="px-4 py-2">¥{row.total_cost_delta_yuan.toFixed(4)}</td>
                  <td className="px-4 py-2">¥{row.current_model_cost_delta_yuan.toFixed(4)}</td>
                </tr>
              ))}
              {data.model_switches.length === 0 && data.model_switch_jobs.slice(0, 5).map((job) => (
                <tr key={job.job_id} className="border-b border-line last:border-0">
                  <td className="px-4 py-2">{formatJobDate(job.created_at)}</td>
                  <td className="px-4 py-2">Job #{job.job_id} fallback × {job.fallback_count}</td>
                  <td className="px-4 py-2">¥{job.total_cost_yuan.toFixed(4)}</td>
                  <td className="px-4 py-2">{formatModelCounts(job.model_counts)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modelSummary.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-line">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line bg-gray-50">
              <tr>
                <th className="px-4 py-2 font-medium text-soft">模型</th>
                <th className="px-4 py-2 font-medium text-soft">调用次数</th>
                <th className="px-4 py-2 font-medium text-soft">输入 tokens</th>
                <th className="px-4 py-2 font-medium text-soft">输出 tokens</th>
                <th className="px-4 py-2 font-medium text-soft">费用</th>
                <th className="px-4 py-2 font-medium text-soft">缓存命中</th>
              </tr>
            </thead>
            <tbody>
              {modelSummary.map((row) => (
                <tr key={row.model} className="border-b border-line last:border-0">
                  <td className="px-4 py-2 font-medium text-ink">{row.model}</td>
                  <td className="px-4 py-2">{row.calls.toLocaleString()}</td>
                  <td className="px-4 py-2">{row.tokens_in.toLocaleString()}</td>
                  <td className="px-4 py-2">{row.tokens_out.toLocaleString()}</td>
                  <td className="px-4 py-2 font-medium">¥{row.cost.toFixed(4)}</td>
                  <td className="px-4 py-2">{row.cache_hits}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
