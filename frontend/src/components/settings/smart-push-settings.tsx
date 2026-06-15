"use client";

import { useEffect, useState } from "react";

import { fetchSmartPushSettings, saveSmartPushSettings } from "@/lib/api/browser";
import type {
  DeptContactSettings,
  DeptMappingItem,
  EscalationRuleSettings,
  PeriodicPushSettings,
  SmartPushSettingsResponse,
} from "@/lib/api/types";

const DEPT_LABELS: Record<string, string> = {
  qa: "质检",
  product: "产研",
  ops: "运营",
  cs: "客服",
  other: "其他",
};

const FREQUENCY_OPTIONS = [
  { value: "daily", label: "每天" },
  { value: "weekly", label: "每周" },
  { value: "biweekly", label: "每两周" },
  { value: "monthly", label: "每月" },
];

const DAY_OPTIONS = [
  { value: "monday", label: "周一" },
  { value: "tuesday", label: "周二" },
  { value: "wednesday", label: "周三" },
  { value: "thursday", label: "周四" },
  { value: "friday", label: "周五" },
  { value: "saturday", label: "周六" },
  { value: "sunday", label: "周日" },
];

export function SmartPushSettingsPanel() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [periodicPush, setPeriodicPush] = useState<PeriodicPushSettings>({
    enabled: false,
    frequency: "weekly",
    day_of_week: "monday",
    day_of_month: 1,
    time: "09:00",
    timezone: "Asia/Shanghai",
  });

  const [deptContacts, setDeptContacts] = useState<DeptContactSettings>({
    qa: "",
    product: "",
    ops: "",
    cs: "",
    other: "",
  });

  const [escalationRules, setEscalationRules] = useState<EscalationRuleSettings>({
    consecutive_count: 3,
    top_n: 3,
    pct_threshold: 10.0,
  });

  const [deptMapping, setDeptMapping] = useState<DeptMappingItem[]>([]);

  useEffect(() => {
    fetchSmartPushSettings()
      .then((data) => {
        setPeriodicPush(data.periodic_push);
        setDeptContacts(data.dept_contacts);
        setEscalationRules(data.escalation_rules);
        setDeptMapping(data.dept_mapping);
      })
      .catch(() => setError("加载智能推送设置失败"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setError("");
    setMessage("");
    setSaving(true);
    try {
      await saveSmartPushSettings({
        periodic_push: periodicPush,
        dept_contacts: deptContacts,
        escalation_rules: escalationRules,
        dept_mapping: deptMapping,
      });
      setMessage("智能推送设置已保存");
    } catch (err) {
      setError((err as { message?: string }).message || "保存失败");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="p-4 text-gray-500">加载中...</div>;
  }

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">智能推送设置</h3>

      {/* 周期推送配置 */}
      <section className="rounded-lg border p-4 space-y-3">
        <h4 className="font-medium">周期推送</h4>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={periodicPush.enabled}
            onChange={(e) => setPeriodicPush({ ...periodicPush, enabled: e.target.checked })}
          />
          <span className="text-sm">启用周期推送</span>
        </label>

        {periodicPush.enabled && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500">推送频率</label>
              <select
                className="w-full rounded border px-2 py-1 text-sm"
                value={periodicPush.frequency}
                onChange={(e) => setPeriodicPush({ ...periodicPush, frequency: e.target.value as PeriodicPushSettings["frequency"] })}
              >
                {FREQUENCY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {(periodicPush.frequency === "weekly" || periodicPush.frequency === "biweekly") && (
              <div>
                <label className="text-xs text-gray-500">推送日</label>
                <select
                  className="w-full rounded border px-2 py-1 text-sm"
                  value={periodicPush.day_of_week}
                  onChange={(e) => setPeriodicPush({ ...periodicPush, day_of_week: e.target.value })}
                >
                  {DAY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            )}

            {periodicPush.frequency === "monthly" && (
              <div>
                <label className="text-xs text-gray-500">每月几号</label>
                <input
                  type="number"
                  min={1}
                  max={28}
                  className="w-full rounded border px-2 py-1 text-sm"
                  value={periodicPush.day_of_month}
                  onChange={(e) => setPeriodicPush({ ...periodicPush, day_of_month: parseInt(e.target.value) || 1 })}
                />
              </div>
            )}

            <div>
              <label className="text-xs text-gray-500">推送时间</label>
              <input
                type="time"
                className="w-full rounded border px-2 py-1 text-sm"
                value={periodicPush.time}
                onChange={(e) => setPeriodicPush({ ...periodicPush, time: e.target.value })}
              />
            </div>
          </div>
        )}
      </section>

      {/* 部门联系人 */}
      <section className="rounded-lg border p-4 space-y-3">
        <h4 className="font-medium">部门负责人（飞书 Open ID）</h4>
        <p className="text-xs text-gray-500">
          配置后推送消息将 @对应负责人。获取方式：飞书管理后台 → 通讯录 → 成员详情 → Open ID
        </p>
        <div className="grid grid-cols-1 gap-2">
          {(Object.keys(DEPT_LABELS) as Array<keyof DeptContactSettings>).map((dept) => (
            <div key={dept} className="flex items-center gap-2">
              <span className="w-16 text-sm font-medium">{DEPT_LABELS[dept]}</span>
              <input
                type="text"
                className="flex-1 rounded border px-2 py-1 text-sm font-mono"
                placeholder={`ou_xxx (${DEPT_LABELS[dept]}负责人)`}
                value={deptContacts[dept]}
                onChange={(e) => setDeptContacts({ ...deptContacts, [dept]: e.target.value })}
              />
            </div>
          ))}
        </div>
      </section>

      {/* 升级规则 */}
      <section className="rounded-lg border p-4 space-y-3">
        <h4 className="font-medium">升级规则</h4>
        <p className="text-xs text-gray-500">
          当某问题连续 N 个推送周期满足条件时，自动升级并生成行动建议
        </p>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-gray-500">连续周期数</label>
            <input
              type="number"
              min={2}
              max={10}
              className="w-full rounded border px-2 py-1 text-sm"
              value={escalationRules.consecutive_count}
              onChange={(e) => setEscalationRules({ ...escalationRules, consecutive_count: parseInt(e.target.value) || 3 })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">TOP N 阈值</label>
            <input
              type="number"
              min={1}
              max={10}
              className="w-full rounded border px-2 py-1 text-sm"
              value={escalationRules.top_n}
              onChange={(e) => setEscalationRules({ ...escalationRules, top_n: parseInt(e.target.value) || 3 })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">占比阈值 (%)</label>
            <input
              type="number"
              min={1}
              max={50}
              step={0.5}
              className="w-full rounded border px-2 py-1 text-sm"
              value={escalationRules.pct_threshold}
              onChange={(e) => setEscalationRules({ ...escalationRules, pct_threshold: parseFloat(e.target.value) || 10 })}
            />
          </div>
        </div>
        <p className="text-xs text-gray-400">
          条件为 OR 关系：连续 {escalationRules.consecutive_count} 期在 TOP {escalationRules.top_n} 或占比超 {escalationRules.pct_threshold}% 时升级
        </p>
      </section>

      {/* 保存按钮 */}
      <div className="flex items-center gap-3">
        <button
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "保存中..." : "保存设置"}
        </button>
        {message && <span className="text-sm text-green-600">{message}</span>}
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>
    </div>
  );
}
