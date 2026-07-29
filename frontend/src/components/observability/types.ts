export type TimeRange = "1h" | "6h" | "24h" | "7d" | "30d";

export type PipelineHealth = {
  summary: {
    total_calls: number;
    error_count: number;
    error_rate: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
    avg_latency_ms: number;
  };
  daily: {
    date: string;
    calls: number;
    errors: number;
    avg_latency_ms: number;
  }[];
};

export type CacheEffectiveness = {
  summary: {
    total_reviews: number;
    total_llm_calls: number;
    cache_saves: number;
    savings_pct: number;
    estimated_cost_saved_yuan: number;
  };
  daily: {
    date: string;
    reviews: number;
    llm_calls: number;
    saved: number;
    savings_pct: number;
  }[];
};

export type ModelStatus = {
  models: Record<
    string,
    {
      available: boolean;
      has_api_key: boolean;
      consecutive_failures: number;
      circuit_open: boolean;
    }
  >;
};

export type LlmCosts = {
  summary: {
    total_cost_yuan: number;
    total_calls: number;
    cache_hits: number;
    cache_rate: number;
    avg_cost_per_call: number;
  };
  daily: {
    date: string;
    model: string;
    calls: number;
    tokens_in: number;
    tokens_out: number;
    cost_yuan: number;
    cache_hits: number;
  }[];
};

export type JobTrace = {
  job_id: number;
  status: string;
  raw_status: string;
  created_at: string;
  completed_at: string | null;
  total_rows: number;
  processed_rows: number;
  session_id: number | null;
  product_id: string | null;
  product_ref_id: number | null;
  variant_ref_id: number | null;
  credit_charged: boolean;
  partial_completed: boolean;
  failure_stage: string | null;
  error_type: string | null;
  total_duration_ms: number | null;
  llm_calls: number | null;
  cache_hits: number | null;
  total_cost_yuan: number | null;
  error: string | null;
  stages: {
    name: string;
    duration_ms: number;
    meta: Record<string, unknown>;
    error: string | null;
  }[];
  decisions: TraceEntry[];
  events: TraceEntry[];
  warnings: TraceEntry[];
  dropped_counts: Record<string, number>;
};

export type TraceEntry = {
  name: string;
  at?: number;
  details?: Record<string, unknown>;
};

export type JobTracesResponse = {
  total: number;
  traces: JobTrace[];
};

export type AlertSeverity = "warning" | "critical";

export type AlertThresholds = {
  llm_error_rate_warning_pct: number;
  llm_error_rate_critical_pct: number;
  llm_p95_warning_ms: number;
  llm_p95_critical_ms: number;
  user_daily_cost_warning_yuan: number;
  user_daily_cost_critical_yuan: number;
  system_daily_cost_warning_yuan: number;
  system_daily_cost_critical_yuan: number;
  cache_savings_warning_pct: number;
  cache_savings_critical_pct: number;
  cache_min_reviews: number;
  stuck_job_warning_minutes: number;
  stuck_job_critical_minutes: number;
};

export type AlertConfig = {
  enabled: boolean;
  webhook_enabled: boolean;
  webhook_platform: "feishu" | "dingtalk" | "wechat";
  webhook_url: string;
  webhook_secret: string;
  webhook_group_name: string;
  dedupe_ttl_seconds: number;
  thresholds: AlertThresholds;
};

export type AlertItem = {
  id: string;
  type: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  metric_value: number | string | null;
  threshold: number | string | null;
  unit: string;
  scope: "user" | "system";
  details: Record<string, unknown>;
  triggered_at: string;
  dedupe_key: string;
  last_sent_at: string | null;
};

export type AlertHistoryItem = Omit<AlertItem, "triggered_at" | "dedupe_key" | "last_sent_at"> & {
  event_id: number;
  notification_status: "sent" | "failed" | "no_webhook" | string;
  notification_message: string;
  created_at: string;
};

export type AlertConfigResponse = {
  config: AlertConfig;
  current_alerts: AlertItem[];
  history: AlertHistoryItem[];
  last_sent_at: Record<string, string>;
};

export function timeRangeToWindowHours(range: TimeRange): number {
  switch (range) {
    case "1h":
      return 1;
    case "6h":
      return 6;
    case "24h":
      return 24;
    case "7d":
      return 7 * 24;
    case "30d":
      return 30 * 24;
  }
}

export function timeRangeUsesHourlyBuckets(range: TimeRange): boolean {
  return range === "1h" || range === "6h" || range === "24h";
}

export function timeRangeToAnalyticsQuery(range: TimeRange): string {
  if (timeRangeUsesHourlyBuckets(range)) {
    return `window_hours=${timeRangeToWindowHours(range)}`;
  }

  return `days=${range === "7d" ? 7 : 30}`;
}

export function formatBucketLabel(value: string, range: TimeRange): string {
  if (timeRangeUsesHourlyBuckets(range)) {
    const parsed = new Date(value.replace(" ", "T"));
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
      });
    }
    return value.length >= 16 ? value.slice(11, 16) : value;
  }

  return value.length >= 10 ? value.slice(5, 10) : value;
}

export function formatTimeRangeLabel(range: TimeRange): string {
  switch (range) {
    case "1h":
      return "最近 1 小时";
    case "6h":
      return "最近 6 小时";
    case "24h":
      return "最近 24 小时";
    case "7d":
      return "最近 7 天";
    case "30d":
      return "最近 30 天";
  }
}

export async function fetchAnalytics<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`/api/analytics/${path}`, {
    ...init,
    credentials: "include",
    cache: "no-store",
    headers,
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<T>;
}
