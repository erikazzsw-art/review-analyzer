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
import type { TimeRange, CacheEffectiveness } from "./types";
import { fetchAnalytics, timeRangeToDays } from "./types";

type Props = { timeRange: TimeRange };

export function CacheTab({ timeRange }: Props) {
  const [data, setData] = useState<CacheEffectiveness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchAnalytics<CacheEffectiveness>(`cache-effectiveness?days=${timeRangeToDays(timeRange)}`)
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

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="总评论数" value={data.summary.total_reviews.toLocaleString()} />
        <StatCard label="LLM 调用" value={data.summary.total_llm_calls.toLocaleString()} />
        <StatCard
          label="缓存节省率"
          value={`${data.summary.savings_pct.toFixed(1)}%`}
          sub={`${data.summary.cache_saves} 次节省`}
          accent="success"
        />
        <StatCard
          label="节省费用"
          value={`¥${data.summary.estimated_cost_saved_yuan.toFixed(2)}`}
          accent="success"
        />
      </div>

      {chartData.length > 0 && (
        <>
          <div className="rounded-xl border border-line bg-white p-4">
            <h3 className="mb-3 text-sm font-medium text-soft">LLM 调用 vs 缓存命中</h3>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="llm_calls" name="LLM调用" fill="#8d7be8" />
                  <Bar dataKey="saved" name="缓存命中" fill="#47c9af" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-xl border border-line bg-white p-4">
            <h3 className="mb-3 text-sm font-medium text-soft">节省率趋势</h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                  <Tooltip formatter={(v) => `${Number(v).toFixed(1)}%`} />
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
