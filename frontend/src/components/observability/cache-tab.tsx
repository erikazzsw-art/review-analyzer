"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
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
import { getCacheSavingsStatus, statusToAccent } from "./metric-status";
import type { TimeRange, CacheEffectiveness } from "./types";
import {
  fetchAnalytics,
  formatBucketLabel,
  formatTimeRangeLabel,
  timeRangeToAnalyticsQuery,
  timeRangeUsesHourlyBuckets,
} from "./types";

type Props = { timeRange: TimeRange };

export function CacheTab({ timeRange }: Props) {
  const [data, setData] = useState<CacheEffectiveness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchAnalytics<CacheEffectiveness>(`cache-effectiveness?${timeRangeToAnalyticsQuery(timeRange)}`)
      .then(setData)
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

  if (!data) return null;

  const chartData = [...data.daily].reverse();
  const hasCacheEvents = data.summary.total_reviews > 0 || data.daily.length > 0;
  const savingsStatus = hasCacheEvents ? getCacheSavingsStatus(data.summary.savings_pct) : undefined;
  const bucketLabel = timeRangeUsesHourlyBuckets(timeRange) ? "小时" : "每日";
  const rangeLabel = formatTimeRangeLabel(timeRange);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          label="总评论数"
          value={data.summary.total_reviews.toLocaleString()}
          description={`${rangeLabel}内完成分析的评论总量，来自 analysis_job_complete 事件。`}
          normalRange="应与完成的上传任务规模一致；为 0 表示当前窗口没有完成事件。"
          actionHint="切到任务 Tab 确认任务是否已完成并写入 trace。"
        />
        <StatCard
          label="LLM 调用"
          value={data.summary.total_llm_calls.toLocaleString()}
          description="完成任务中实际需要模型处理的调用数。缓存越有效，这个数字相对评论数越低。"
          normalRange="重复评论较多时应明显低于总评论数。"
          actionHint="如果与总评论数接近，检查缓存命中来源和重复上传场景。"
        />
        <StatCard
          label="缓存节省率"
          value={`${data.summary.savings_pct.toFixed(1)}%`}
          sub={`${data.summary.cache_saves} 次节省`}
          accent={savingsStatus ? statusToAccent(savingsStatus) : "default"}
          status={savingsStatus}
          description="缓存或聚类复用帮你省掉的 LLM 调用比例。它越高，成本和等待时间越可控。"
          normalRange="≥ 50% 正常；35%-50% 注意，20%-35% 异常，< 20% 严重。首次上传或新品类可暂时偏低。"
          actionHint="重复上传仍偏低时，检查缓存写入、相似度阈值和聚类传播是否生效。"
        />
        <StatCard
          label="节省费用"
          value={`¥${data.summary.estimated_cost_saved_yuan.toFixed(2)}`}
          accent="success"
          description="根据节省调用数估算少花的模型费用，用于判断缓存策略带来的直接收益。"
          normalRange="应随缓存节省率和评论量增加而上升。"
          actionHint="如果节省率高但金额低，通常只是当前窗口评论量较少。"
        />
      </div>

      {!hasCacheEvents && (
        <EmptyDataNotice
          title="暂无缓存效果事件"
          description="缓存页依赖 analytics_events 里的 analysis_job_complete 事件；没有数据通常是当前时间范围内没有完成的分析任务，或任务完成后未写入统计事件。"
          action="切换到 7天/30天，或完成一次新上传后检查 analytics_events 是否出现 analysis_job_complete。"
        />
      )}

      {chartData.length > 0 && (
        <>
          <div className="rounded-xl border border-line bg-white p-4">
            <h3 className="mb-3 text-sm font-medium text-soft">{bucketLabel} LLM 调用 vs 缓存命中</h3>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(value) => formatBucketLabel(String(value), timeRange)}
                  />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip labelFormatter={(value) => formatBucketLabel(String(value), timeRange)} />
                  <Legend />
                  <Bar dataKey="llm_calls" name="LLM调用" fill="#8d7be8" />
                  <Bar dataKey="saved" name="缓存命中" fill="#47c9af" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-xl border border-line bg-white p-4">
            <h3 className="mb-3 text-sm font-medium text-soft">{bucketLabel}节省率趋势</h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(value) => formatBucketLabel(String(value), timeRange)}
                  />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                  <Tooltip
                    formatter={(v) => `${Number(v).toFixed(1)}%`}
                    labelFormatter={(value) => formatBucketLabel(String(value), timeRange)}
                  />
                  <Line
                    type="monotone"
                    dataKey="savings_pct"
                    name="节省率"
                    stroke="#47c9af"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
