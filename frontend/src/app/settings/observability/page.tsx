"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

type PipelineHealth = {
  summary: {
    total_calls: number;
    error_count: number;
    error_rate: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
    avg_latency_ms: number;
  };
  daily: { date: string; calls: number; errors: number; avg_latency_ms: number }[];
};

type CacheEffectiveness = {
  summary: {
    total_reviews: number;
    total_llm_calls: number;
    cache_saves: number;
    savings_pct: number;
    estimated_cost_saved_yuan: number;
  };
  daily: { date: string; reviews: number; llm_calls: number; saved: number; savings_pct: number }[];
};

type ModelStatus = {
  models: Record<string, {
    available: boolean;
    has_api_key: boolean;
    consecutive_failures: number;
    circuit_open: boolean;
  }>;
};

type JobTrace = {
  job_id: number;
  status: string;
  created_at: string;
  total_duration_ms: number | null;
  llm_calls: number | null;
  cache_hits: number | null;
  total_cost_yuan: number | null;
  error: string | null;
  stages: { name: string; duration_ms: number; meta: Record<string, unknown>; error: string | null }[];
};

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`/api/analytics/${path}`, { credentials: "include", cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<T>;
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-line bg-white p-4">
      <div className="text-xs text-soft">{label}</div>
      <div className="mt-1 text-2xl font-bold text-ink">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-soft">{sub}</div>}
    </div>
  );
}

function ModelCard({ name, info }: { name: string; info: ModelStatus["models"][string] }) {
  const statusColor = info.circuit_open
    ? "bg-red-100 text-red-700"
    : info.available
      ? "bg-emerald-100 text-emerald-700"
      : "bg-yellow-100 text-yellow-700";
  const statusLabel = info.circuit_open
    ? "熔断"
    : info.available
      ? "正常"
      : "不可用";

  return (
    <div className="flex items-center justify-between rounded-lg border border-line bg-white px-4 py-3">
      <div>
        <div className="text-sm font-medium text-ink">{name}</div>
        {info.consecutive_failures > 0 && (
          <div className="text-xs text-soft">连续失败: {info.consecutive_failures}</div>
        )}
      </div>
      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor}`}>
        {statusLabel}
      </span>
    </div>
  );
}

export default function ObservabilityPage() {
  const [health, setHealth] = useState<PipelineHealth | null>(null);
  const [cache, setCache] = useState<CacheEffectiveness | null>(null);
  const [models, setModels] = useState<ModelStatus | null>(null);
  const [traces, setTraces] = useState<JobTrace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchApi<PipelineHealth>("pipeline-health?days=7"),
      fetchApi<CacheEffectiveness>("cache-effectiveness?days=7"),
      fetchApi<ModelStatus>("model-status"),
      fetchApi<{ traces: JobTrace[] }>("job-traces?limit=10"),
    ])
      .then(([h, c, m, t]) => {
        setHealth(h);
        setCache(c);
        setModels(m);
        setTraces(t.traces);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-soft">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-red-600">加载失败: {error}</div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 py-8">
      <h1 className="text-2xl font-bold text-ink">分析链路可观测</h1>

      {/* Pipeline Health Summary */}
      {health && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-ink">管线健康度 (7日)</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="总调用" value={health.summary.total_calls} />
            <StatCard label="错误率" value={`${health.summary.error_rate}%`} sub={`${health.summary.error_count} 次错误`} />
            <StatCard label="P50 延迟" value={`${health.summary.p50_ms}ms`} />
            <StatCard label="P95 延迟" value={`${health.summary.p95_ms}ms`} sub={`P99: ${health.summary.p99_ms}ms`} />
          </div>

          {health.daily.length > 0 && (
            <div className="mt-4 h-56 rounded-xl border border-line bg-white p-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={[...health.daily].reverse()}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="avg_latency_ms" name="平均延迟(ms)" stroke="#8d7be8" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="calls" name="调用数" stroke="#f36f8f" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>
      )}

      {/* Cache Effectiveness */}
      {cache && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-ink">缓存效果 (7日)</h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="总评论数" value={cache.summary.total_reviews} />
            <StatCard label="LLM 调用" value={cache.summary.total_llm_calls} />
            <StatCard label="缓存节省" value={`${cache.summary.savings_pct}%`} sub={`${cache.summary.cache_saves} 次`} />
            <StatCard label="节省费用" value={`¥${cache.summary.estimated_cost_saved_yuan}`} />
          </div>

          {cache.daily.length > 0 && (
            <div className="mt-4 h-56 rounded-xl border border-line bg-white p-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={[...cache.daily].reverse()}>
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
          )}
        </section>
      )}

      {/* Model Status */}
      {models && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-ink">模型状态</h2>
          <div className="grid gap-2 sm:grid-cols-3">
            {Object.entries(models.models).map(([name, info]) => (
              <ModelCard key={name} name={name} info={info} />
            ))}
          </div>
        </section>
      )}

      {/* Job Traces */}
      {traces.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-ink">最近任务追踪</h2>
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
                {traces.map((t) => (
                  <tr key={t.job_id} className="border-b border-line last:border-0">
                    <td className="px-4 py-2 font-mono text-xs">{t.job_id}</td>
                    <td className="px-4 py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        t.status === "completed" ? "bg-emerald-100 text-emerald-700" :
                        t.status === "failed" ? "bg-red-100 text-red-700" :
                        "bg-yellow-100 text-yellow-700"
                      }`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-xs">{t.total_duration_ms ? `${(t.total_duration_ms / 1000).toFixed(1)}s` : "-"}</td>
                    <td className="px-4 py-2 text-xs">{t.llm_calls ?? "-"}</td>
                    <td className="px-4 py-2 text-xs">{t.cache_hits ?? "-"}</td>
                    <td className="px-4 py-2 text-xs">{t.total_cost_yuan ? `¥${t.total_cost_yuan.toFixed(4)}` : "-"}</td>
                    <td className="px-4 py-2 text-xs text-soft">{new Date(t.created_at).toLocaleString("zh-CN")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
