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
import type { TimeRange, LlmCosts } from "./types";
import { fetchAnalytics, timeRangeToDays } from "./types";

const MODEL_COLORS: Record<string, string> = {
  "deepseek-chat": "#8d7be8",
  "gpt-4o-mini": "#f36f8f",
  "qwen-plus": "#47c9af",
};

function getModelColor(model: string): string {
  return MODEL_COLORS[model] || "#94a3b8";
}

type Props = { timeRange: TimeRange };

export function CostTab({ timeRange }: Props) {
  const [data, setData] = useState<LlmCosts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchAnalytics<LlmCosts>(`llm-costs?days=${timeRangeToDays(timeRange)}`)
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

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          label="总费用"
          value={`¥${data.summary.total_cost_yuan.toFixed(2)}`}
        />
        <StatCard label="总调用" value={data.summary.total_calls} />
        <StatCard
          label="缓存命中率"
          value={`${data.summary.cache_rate.toFixed(1)}%`}
          sub={`${data.summary.cache_hits} 次命中`}
        />
        <StatCard
          label="平均单次成本"
          value={`¥${data.summary.avg_cost_per_call.toFixed(4)}`}
        />
      </div>

      {chartData.length > 0 && (
        <div className="rounded-xl border border-line bg-white p-4">
          <h3 className="mb-3 text-sm font-medium text-soft">每日成本 (按模型)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `¥${v}`} />
                <Tooltip formatter={(v) => `¥${Number(v).toFixed(4)}`} />
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
