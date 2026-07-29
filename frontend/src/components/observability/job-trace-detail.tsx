"use client";

import { cn } from "@/lib/utils";
import type { JobTrace, TraceEntry } from "./types";

type Props = { trace: JobTrace };

const ENTRY_LABELS: Record<string, string> = {
  job_context: "任务上下文",
  taxonomy: "Taxonomy",
  analysis_scope: "分析范围",
  prompt_config: "Prompt 配置",
  cache_lookup: "缓存判定",
  clustering: "聚类决策",
  cluster_propagation: "聚类传播",
  llm_non_embedding_batch: "无 embedding 批次",
  llm_prompt_quality: "Prompt 与质量",
  result_sources: "结果来源",
  llm_router_chain: "模型路由链",
  llm_provider_attempt: "Provider attempt",
  llm_provider_success: "Provider success",
  llm_provider_failure: "Provider failure",
  llm_provider_fallback: "Provider fallback",
  llm_provider_circuit: "Provider circuit",
  llm_provider_429_retry: "429 retry",
  llm_provider_skipped: "Provider skipped",
  llm_quality: "LLM 质量",
  llm_quality_warning: "LLM 质量告警",
  taxonomy_coverage: "Taxonomy 覆盖率",
  cluster_needs_llm: "低质聚类",
};

const KEY_LABELS: Record<string, string> = {
  prompt_version: "Prompt",
  locale: "Locale",
  sub_category: "品类",
  provider_chain: "路由链",
  provider: "Provider",
  model: "模型",
  model_counts: "模型分布",
  route_events: "路由事件",
  retry_distribution: "Retry 分布",
  retry_count: "Retry",
  retry_count_total: "Retry 总数",
  json_decode: "JSON 解析",
  schema_invalid: "Schema",
  final_success: "最终成功",
  final_failure: "最终失败",
  hit_sources: "命中来源",
  cache_hit_sources: "缓存来源",
  miss_reasons: "Miss 原因",
  cluster_count: "簇数",
  representatives_count: "代表数",
  needs_llm_count: "需 LLM",
  direct_llm_count: "直接 LLM",
  cluster_propagated_count: "聚类传播",
  skipped_reason: "跳过原因",
  error_type: "错误类型",
  error_detail: "错误详情",
  schema_error: "Schema 错误",
  wait_seconds: "等待秒数",
  cooldown_remaining_seconds: "熔断剩余",
};

const VALUE_LABELS: Record<string, string> = {
  user_history: "本人历史",
  global_review_pool: "全局 review_pool",
  semantic_similar: "语义相似",
  short_text_rating_rule: "短文本评分规则",
  exact_hash: "精确 hash",
  embedding_missing: "缺少 embedding",
  semantic_reference_unavailable: "无语义参考池",
  semantic_similarity_below_threshold: "语义相似度不足",
  embeddings_unavailable: "embedding 不可用",
  batch_too_small: "批量过小",
  no_cache_misses: "缓存全命中",
  low_cluster_similarity: "簇内相似度低",
  disabled_provider: "本次禁用",
  missing_api_key: "未配置 API Key",
  max_model_attempts_reached: "达到尝试上限",
};

function labelFor(value: string, labels: Record<string, string>) {
  return labels[value] || value;
}

function formatTime(seconds?: number) {
  if (!seconds) return "";
  return new Date(seconds * 1000).toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatPrimitive(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  if (typeof value === "string") return labelFor(value, VALUE_LABELS);
  return "";
}

function formatValue(value: unknown): string {
  const primitive = formatPrimitive(value);
  if (primitive) return primitive;
  if (Array.isArray(value)) {
    return value.map((item) => formatValue(item)).join(", ");
  }
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

function detailPairs(entry: TraceEntry) {
  return Object.entries(entry.details || {}).slice(0, 12);
}

function TraceSection({
  title,
  entries,
  tone,
  empty,
}: {
  title: string;
  entries: TraceEntry[];
  tone: "blue" | "emerald" | "amber";
  empty: string;
}) {
  const toneClass = {
    blue: "border-sky-200 bg-sky-50 text-sky-800",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-800",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
  }[tone];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-soft">{title}</span>
        <span className="text-soft">{entries.length}</span>
      </div>
      {entries.length > 0 ? (
        <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
          {entries.map((entry, index) => (
            <div key={`${entry.name}-${index}`} className={cn("rounded-lg border px-3 py-2 text-xs", toneClass)}>
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">{labelFor(entry.name, ENTRY_LABELS)}</span>
                {entry.at && <span className="shrink-0 opacity-70">{formatTime(entry.at)}</span>}
              </div>
              {detailPairs(entry).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {detailPairs(entry).map(([key, value]) => (
                    <span key={key} className="max-w-full rounded-md bg-white/70 px-2 py-1">
                      <span className="opacity-70">{labelFor(key, KEY_LABELS)}: </span>
                      <span className="break-all font-medium">{formatValue(value)}</span>
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs text-soft">{empty}</div>
      )}
    </div>
  );
}

export function JobTraceDetail({ trace }: Props) {
  const stages = trace.stages || [];
  const decisions = trace.decisions || [];
  const events = trace.events || [];
  const warnings = trace.warnings || [];
  const droppedCounts = trace.dropped_counts || {};
  const totalMs = trace.total_duration_ms || stages.reduce((sum, s) => sum + s.duration_ms, 0) || 1;

  return (
    <div className="space-y-3 border-t border-line bg-gray-50 px-4 py-3">
      {stages.length > 0 ? (
        <>
          <div className="text-xs font-medium text-soft">执行阶段</div>
          <div className="flex h-6 w-full overflow-hidden rounded-full bg-gray-200">
            {stages.map((stage, i) => {
              const pct = (stage.duration_ms / totalMs) * 100;
              if (pct < 0.5) return null;
              const colors = [
                "bg-violet-400",
                "bg-rose-400",
                "bg-emerald-400",
                "bg-amber-400",
                "bg-sky-400",
              ];
              return (
                <div
                  key={i}
                  className={cn("relative h-full", colors[i % colors.length])}
                  style={{ width: `${pct}%` }}
                  title={`${stage.name}: ${stage.duration_ms}ms`}
                />
              );
            })}
          </div>
          <div className="space-y-1">
            {stages.map((stage, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "h-2.5 w-2.5 rounded-sm",
                      ["bg-violet-400", "bg-rose-400", "bg-emerald-400", "bg-amber-400", "bg-sky-400"][i % 5],
                    )}
                  />
                  <span className="text-ink">{stage.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-soft">{stage.duration_ms}ms</span>
                  {stage.error && (
                    <span className="text-red-600">{stage.error}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="space-y-1 text-xs text-soft">
          <div className="font-medium text-ink">无阶段追踪数据</div>
          <p>
            这个任务没有写入 stages，可能是旧版本任务、任务尚未进入处理阶段，或 worker 没有成功持久化 trace。
            下一步可查看任务状态和错误信息，必要时重新上传一次以生成新版 trace。
          </p>
        </div>
      )}

      {trace.error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {trace.error}
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-3">
        <TraceSection title="关键决策" entries={decisions} tone="blue" empty="暂无决策记录" />
        <TraceSection title="路由与质量事件" entries={events} tone="emerald" empty="暂无事件记录" />
        <TraceSection title="警告" entries={warnings} tone="amber" empty="暂无警告" />
      </div>

      {Object.keys(droppedCounts).length > 0 && (
        <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs text-soft">
          Trace 已截断: {formatValue(droppedCounts)}
        </div>
      )}
    </div>
  );
}
