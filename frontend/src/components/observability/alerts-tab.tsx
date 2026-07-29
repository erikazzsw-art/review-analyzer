"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Bell, CheckCircle2, RefreshCw, Save } from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  AlertConfig,
  AlertConfigResponse,
  AlertHistoryItem,
  AlertItem,
  AlertThresholds,
} from "./types";
import { fetchAnalytics } from "./types";

type ThresholdField = {
  key: keyof AlertThresholds;
  label: string;
  unit: string;
};

const THRESHOLD_FIELDS: ThresholdField[] = [
  { key: "llm_error_rate_warning_pct", label: "错误率 Warning", unit: "%" },
  { key: "llm_error_rate_critical_pct", label: "错误率 Critical", unit: "%" },
  { key: "llm_p95_warning_ms", label: "P95 Warning", unit: "ms" },
  { key: "llm_p95_critical_ms", label: "P95 Critical", unit: "ms" },
  { key: "user_daily_cost_warning_yuan", label: "用户日成本 Warning", unit: "¥" },
  { key: "user_daily_cost_critical_yuan", label: "用户日成本 Critical", unit: "¥" },
  { key: "system_daily_cost_warning_yuan", label: "系统日成本 Warning", unit: "¥" },
  { key: "system_daily_cost_critical_yuan", label: "系统日成本 Critical", unit: "¥" },
  { key: "cache_savings_warning_pct", label: "缓存节省率 Warning", unit: "%" },
  { key: "cache_savings_critical_pct", label: "缓存节省率 Critical", unit: "%" },
  { key: "cache_min_reviews", label: "缓存最小评论数", unit: "条" },
  { key: "stuck_job_warning_minutes", label: "卡死 Warning", unit: "min" },
  { key: "stuck_job_critical_minutes", label: "卡死 Critical", unit: "min" },
];

const SEVERITY_STYLES = {
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  critical: "border-red-200 bg-red-50 text-red-700",
};

const STATUS_LABELS: Record<string, string> = {
  sent: "已发送",
  failed: "发送失败",
  no_webhook: "未配置 Webhook",
  deduped: "已去重",
};

function formatTime(value: string | null | undefined) {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("zh-CN");
}

function formatMetric(value: number | string | null, unit: string) {
  if (value === null || value === undefined || value === "") return "-";
  if (unit === "yuan") return `¥${Number(value).toFixed(2)}`;
  if (unit === "%") return `${Number(value).toFixed(1)}%`;
  return `${value}${unit ? ` ${unit}` : ""}`;
}

function severityLabel(severity: AlertItem["severity"]) {
  return severity === "critical" ? "严重" : "注意";
}

function AlertBadge({ severity }: { severity: AlertItem["severity"] }) {
  return (
    <span className={cn("inline-flex rounded-full border px-2 py-0.5 text-xs font-medium", SEVERITY_STYLES[severity])}>
      {severityLabel(severity)}
    </span>
  );
}

function AlertTable({
  alerts,
  empty,
}: {
  alerts: AlertItem[];
  empty: string;
}) {
  if (alerts.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-700">
        <CheckCircle2 className="h-4 w-4" />
        {empty}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-line">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-line bg-gray-50">
          <tr>
            <th className="px-3 py-2 font-medium text-soft">级别</th>
            <th className="px-3 py-2 font-medium text-soft">告警</th>
            <th className="px-3 py-2 font-medium text-soft">指标</th>
            <th className="px-3 py-2 font-medium text-soft">阈值</th>
            <th className="px-3 py-2 font-medium text-soft">范围</th>
            <th className="px-3 py-2 font-medium text-soft">最近发送</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.id} className="border-b border-line last:border-0">
              <td className="px-3 py-2"><AlertBadge severity={alert.severity} /></td>
              <td className="px-3 py-2">
                <div className="font-medium text-ink">{alert.title}</div>
                <div className="max-w-[420px] truncate text-xs text-soft">{alert.message}</div>
              </td>
              <td className="px-3 py-2 font-mono text-xs">{formatMetric(alert.metric_value, alert.unit)}</td>
              <td className="px-3 py-2 font-mono text-xs">{formatMetric(alert.threshold, alert.unit)}</td>
              <td className="px-3 py-2 text-xs text-soft">{alert.scope === "system" ? "系统" : "当前用户"}</td>
              <td className="px-3 py-2 text-xs text-soft">{formatTime(alert.last_sent_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HistoryTable({ history }: { history: AlertHistoryItem[] }) {
  if (history.length === 0) {
    return <div className="rounded-lg border border-line px-3 py-4 text-sm text-soft">暂无告警历史</div>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-line">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-line bg-gray-50">
          <tr>
            <th className="px-3 py-2 font-medium text-soft">时间</th>
            <th className="px-3 py-2 font-medium text-soft">级别</th>
            <th className="px-3 py-2 font-medium text-soft">告警</th>
            <th className="px-3 py-2 font-medium text-soft">通知状态</th>
          </tr>
        </thead>
        <tbody>
          {history.map((item) => (
            <tr key={item.event_id} className="border-b border-line last:border-0">
              <td className="px-3 py-2 text-xs text-soft">{formatTime(item.created_at)}</td>
              <td className="px-3 py-2"><AlertBadge severity={item.severity} /></td>
              <td className="px-3 py-2">
                <div className="font-medium text-ink">{item.title}</div>
                <div className="max-w-[520px] truncate text-xs text-soft">{item.message}</div>
              </td>
              <td className="px-3 py-2 text-xs text-soft">
                {STATUS_LABELS[item.notification_status] || item.notification_status || "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AlertsTab() {
  const [data, setData] = useState<AlertConfigResponse | null>(null);
  const [draft, setDraft] = useState<AlertConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchAnalytics<AlertConfigResponse>("alert-config")
      .then((res) => {
        setData(res);
        setDraft(res.config);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function updateDraft<K extends keyof AlertConfig>(key: K, value: AlertConfig[K]) {
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  function updateThreshold(key: keyof AlertThresholds, value: string) {
    const parsed = Number(value);
    setDraft((prev) => (
      prev
        ? {
            ...prev,
            thresholds: {
              ...prev.thresholds,
              [key]: Number.isFinite(parsed) ? parsed : 0,
            },
          }
        : prev
    ));
  }

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetchAnalytics<AlertConfigResponse>("alert-config", {
        method: "PUT",
        body: JSON.stringify(draft),
      });
      setData(res);
      setDraft(res.config);
      setSavedAt(new Date().toLocaleTimeString("zh-CN"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl border border-line bg-gray-50" />
          ))}
        </div>
        <div className="h-64 animate-pulse rounded-xl border border-line bg-gray-50" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-sm text-red-600">
        加载失败: {error}
      </div>
    );
  }

  if (!data || !draft) return null;

  const criticalCount = data.current_alerts.filter((item) => item.severity === "critical").length;
  const warningCount = data.current_alerts.filter((item) => item.severity === "warning").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div className="grid flex-1 gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-line bg-white p-4">
            <div className="flex items-center gap-2 text-xs text-soft">
              <Bell className="h-4 w-4" />
              当前触发
            </div>
            <div className="mt-1 text-2xl font-bold text-ink">{data.current_alerts.length}</div>
          </div>
          <div className="rounded-xl border border-line bg-white p-4">
            <div className="flex items-center gap-2 text-xs text-soft">
              <AlertTriangle className="h-4 w-4" />
              严重 / 注意
            </div>
            <div className="mt-1 text-2xl font-bold text-ink">{criticalCount} / {warningCount}</div>
          </div>
          <div className="rounded-xl border border-line bg-white p-4">
            <div className="text-xs text-soft">去重窗口</div>
            <div className="mt-1 text-2xl font-bold text-ink">{Math.round(draft.dedupe_ttl_seconds / 60)}min</div>
          </div>
        </div>
        <button
          type="button"
          onClick={load}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line text-soft transition-colors hover:text-ink"
          aria-label="刷新告警"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </div>
      )}

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-ink">当前触发中的告警</h3>
        <AlertTable alerts={data.current_alerts} empty="当前无触发中告警" />
      </section>

      <section className="space-y-4 rounded-xl border border-line bg-white p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink">阈值与通知</h3>
          <div className="flex items-center gap-3">
            {savedAt && <span className="text-xs text-soft">已保存 {savedAt}</span>}
            <button
              type="button"
              onClick={save}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-lg bg-ink px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-ink/90 disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {saving ? "保存中" : "保存"}
            </button>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(e) => updateDraft("enabled", e.target.checked)}
              className="h-4 w-4 rounded border-line"
            />
            启用告警扫描
          </label>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={draft.webhook_enabled}
              onChange={(e) => updateDraft("webhook_enabled", e.target.checked)}
              className="h-4 w-4 rounded border-line"
            />
            使用自定义 Webhook
          </label>
          <label className="space-y-1 text-xs text-soft">
            通知平台
            <select
              value={draft.webhook_platform}
              onChange={(e) => updateDraft("webhook_platform", e.target.value as AlertConfig["webhook_platform"])}
              className="h-9 w-full rounded-lg border border-line bg-white px-3 text-sm text-ink"
            >
              <option value="feishu">飞书</option>
              <option value="dingtalk">钉钉</option>
              <option value="wechat">企业微信</option>
            </select>
          </label>
          <label className="space-y-1 text-xs text-soft">
            去重窗口
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={1}
                value={Math.round(draft.dedupe_ttl_seconds / 60)}
                onChange={(e) => updateDraft("dedupe_ttl_seconds", Math.max(1, Number(e.target.value) || 1) * 60)}
                className="h-9 w-full rounded-lg border border-line px-3 text-sm text-ink"
              />
              <span className="text-xs text-soft">min</span>
            </div>
          </label>
          <label className="space-y-1 text-xs text-soft md:col-span-2">
            Webhook URL
            <input
              value={draft.webhook_url}
              onChange={(e) => updateDraft("webhook_url", e.target.value)}
              className="h-9 w-full rounded-lg border border-line px-3 text-sm text-ink"
              placeholder="https://..."
            />
          </label>
          <label className="space-y-1 text-xs text-soft">
            Webhook Secret
            <input
              value={draft.webhook_secret}
              onChange={(e) => updateDraft("webhook_secret", e.target.value)}
              className="h-9 w-full rounded-lg border border-line px-3 text-sm text-ink"
              type="password"
            />
          </label>
          <label className="space-y-1 text-xs text-soft">
            群名称
            <input
              value={draft.webhook_group_name}
              onChange={(e) => updateDraft("webhook_group_name", e.target.value)}
              className="h-9 w-full rounded-lg border border-line px-3 text-sm text-ink"
            />
          </label>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {THRESHOLD_FIELDS.map((field) => (
            <label key={field.key} className="space-y-1 text-xs text-soft">
              {field.label}
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  value={draft.thresholds[field.key]}
                  onChange={(e) => updateThreshold(field.key, e.target.value)}
                  className="h-9 w-full rounded-lg border border-line px-3 text-sm text-ink"
                />
                <span className="w-9 text-xs text-soft">{field.unit}</span>
              </div>
            </label>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-ink">历史告警</h3>
        <HistoryTable history={data.history} />
      </section>
    </div>
  );
}
