"use client";

import { useEffect, useMemo, useState } from "react";

import { fetchSmartPushSettings, saveSettings, saveSmartPushSettings, testWebhook } from "@/lib/api/browser";
import type {
  DeptContactSettings,
  EscalationRuleSettings,
  PeriodicPushSettings,
  ProductRuleSettings,
  PushRuleSettings,
  SettingsResponse,
} from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Props = { initialSettings: SettingsResponse };

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

// --- placeholder for remaining content ---

function RuleToggle({
  label,
  checked,
  value,
  onToggle,
  onValue,
}: {
  label: string;
  checked: boolean;
  value: number;
  onToggle: (checked: boolean) => void;
  onValue: (value: number) => void;
}) {
  return (
    <div className="grid gap-3 rounded-card border border-line bg-white px-4 py-3 md:grid-cols-[1fr_100px]">
      <label className="flex items-center gap-3 text-sm font-medium text-ink">
        <input type="checkbox" checked={checked} onChange={(e) => onToggle(e.target.checked)} />
        {label}
      </label>
      <Input
        type="number"
        value={value}
        min={1}
        max={100}
        onChange={(e) => onValue(Number(e.target.value || 0))}
        className="rounded-card border-line bg-white text-sm"
      />
    </div>
  );
}

export function PushSettingsPanel({ initialSettings }: Props) {
  const [webhookUrl, setWebhookUrl] = useState(initialSettings.webhook_url);
  const [webhookSecret, setWebhookSecret] = useState(initialSettings.webhook_secret);
  const [webhookGroupName, setWebhookGroupName] = useState(initialSettings.webhook_group_name);
  const [rules, setRules] = useState<PushRuleSettings>({ ...initialSettings.rules });
  const [productRules, setProductRules] = useState<ProductRuleSettings[]>(initialSettings.product_rules);

  const [periodicPush, setPeriodicPush] = useState<PeriodicPushSettings>({
    enabled: false, frequency: "weekly", day_of_week: "monday", day_of_month: 1, time: "09:00", timezone: "Asia/Shanghai",
  });
  const [deptContacts, setDeptContacts] = useState<DeptContactSettings>({ qa: "", product: "", ops: "", cs: "", other: "" });
  const [escalationRules, setEscalationRules] = useState<EscalationRuleSettings>({
    consecutive_count: 3, top_n: 3, pct_threshold: 10.0,
  });

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [smartLoading, setSmartLoading] = useState(true);

  useEffect(() => {
    fetchSmartPushSettings()
      .then((data) => {
        setPeriodicPush(data.periodic_push);
        setDeptContacts(data.dept_contacts);
        setEscalationRules(data.escalation_rules);
      })
      .catch(() => {})
      .finally(() => setSmartLoading(false));
  }, []);

  const canSave = useMemo(() => webhookUrl.trim().length > 0, [webhookUrl]);

  function updateRule<K extends keyof PushRuleSettings>(key: K, value: PushRuleSettings[K]) {
    setRules((cur) => ({ ...cur, [key]: value }));
  }

  // --- placeholder2 ---

  async function handleSave() {
    setError(""); setMessage(""); setIsSaving(true);
    try {
      await saveSettings({ webhookUrl: webhookUrl.trim(), webhookSecret: webhookSecret.trim(), webhookGroupName: webhookGroupName.trim(), apiKey: "", rules, productRules });
      await saveSmartPushSettings({ periodic_push: periodicPush, dept_contacts: deptContacts, escalation_rules: escalationRules, dept_mapping: [] });
      setMessage("设置已保存。");
    } catch (err) {
      setError((err as { message?: string }).message || "保存失败");
    } finally { setIsSaving(false); }
  }

  async function handleTestWebhook() {
    setError(""); setMessage(""); setIsTesting(true);
    try {
      const result = await testWebhook({ webhookUrl: webhookUrl.trim(), webhookSecret: webhookSecret.trim() });
      setMessage((result.message as string) || "连接测试完成。");
    } catch (err) {
      setError((err as { message?: string }).message || "测试失败");
    } finally { setIsTesting(false); }
  }

  function removeProductRule(index: number) {
    setProductRules((cur) => cur.filter((_, i) => i !== index));
  }

  function addProductRule() {
    setProductRules((cur) => [...cur, { product_id: "", name: null, issue_pct: 5, neg_rate: 25, hl_pct: 10, enabled: true }]);
  }

  return (
    <div className="space-y-5">
      {/* ① 绑定飞书 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">绑定飞书</h2>
        <p className="mt-1 text-sm text-soft">配置飞书群机器人 Webhook，启用自动推送。</p>
        <div className="mt-5 space-y-4">
          <label className="block space-y-1">
            <span className="text-sm font-semibold text-ink">Webhook URL</span>
            <Input value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." className="rounded-card border-line" />
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block space-y-1">
              <span className="text-sm font-semibold text-ink">加签密钥</span>
              <Input type="password" value={webhookSecret} onChange={(e) => setWebhookSecret(e.target.value)} className="rounded-card border-line" />
            </label>
            <label className="block space-y-1">
              <span className="text-sm font-semibold text-ink">群名称备注</span>
              <Input value={webhookGroupName} onChange={(e) => setWebhookGroupName(e.target.value)} className="rounded-card border-line" />
            </label>
          </div>
          <Button type="button" variant="outline" onClick={handleTestWebhook} disabled={isTesting} className="rounded-pill border-line px-5 py-2 text-sm font-semibold">
            {isTesting ? "测试中..." : "测试连接"}
          </Button>
        </div>
      </section>

      {/* ② 全局触发规则 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">全局触发规则</h2>
        <p className="mt-1 text-sm text-soft">满足以下任一条件时自动推送。环比窗口固定 14 天。</p>
        <div className="mt-4 space-y-3">
          <RuleToggle label="问题占比 ≥" checked={rules.issue_pct_enabled} value={rules.issue_pct_threshold} onToggle={(v) => updateRule("issue_pct_enabled", v)} onValue={(v) => updateRule("issue_pct_threshold", v)} />
          <RuleToggle label="负面率 ≥" checked={rules.neg_rate_enabled} value={rules.neg_rate_threshold} onToggle={(v) => updateRule("neg_rate_enabled", v)} onValue={(v) => updateRule("neg_rate_threshold", v)} />
          <RuleToggle label="负面率环比（14天）≥" checked={rules.neg_rate_compare_enabled} value={rules.neg_rate_compare_threshold} onToggle={(v) => updateRule("neg_rate_compare_enabled", v)} onValue={(v) => updateRule("neg_rate_compare_threshold", v)} />
          <RuleToggle label="问题环比（14天）≥" checked={rules.issue_compare_enabled} value={rules.issue_compare_threshold} onToggle={(v) => updateRule("issue_compare_enabled", v)} onValue={(v) => updateRule("issue_compare_threshold", v)} />
          <RuleToggle label="亮点占比 ≥" checked={rules.highlight_pct_enabled} value={rules.highlight_pct_threshold} onToggle={(v) => updateRule("highlight_pct_enabled", v)} onValue={(v) => updateRule("highlight_pct_threshold", v)} />
          <RuleToggle label="亮点环比（14天）≥" checked={rules.highlight_compare_enabled} value={rules.highlight_compare_threshold} onToggle={(v) => updateRule("highlight_compare_enabled", v)} onValue={(v) => updateRule("highlight_compare_threshold", v)} />
          <label className="flex items-center gap-3 rounded-card border border-line bg-white px-4 py-3 text-sm text-ink">
            <input type="checkbox" checked={rules.auto_push_new_batch} onChange={(e) => updateRule("auto_push_new_batch", e.target.checked)} />
            新批次自动推送
          </label>
        </div>
      </section>

      {/* ③ 产品级专项规则 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">产品级专项规则</h2>
        <p className="mt-1 text-sm text-soft">为特定产品设置独立的告警阈值。</p>
        <div className="mt-4 space-y-3">
          {productRules.map((rule, idx) => (
            <div key={idx} className="rounded-card border border-line bg-white p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Input value={rule.product_id} onChange={(e) => { const next = [...productRules]; next[idx] = { ...rule, product_id: e.target.value }; setProductRules(next); }} placeholder="产品 ID" className="flex-1 rounded-card border-line text-sm" />
                <label className="flex items-center gap-1 text-xs text-soft">
                  <input type="checkbox" checked={rule.enabled} onChange={(e) => { const next = [...productRules]; next[idx] = { ...rule, enabled: e.target.checked }; setProductRules(next); }} />
                  启用
                </label>
                <button type="button" onClick={() => removeProductRule(idx)} className="text-xs text-red-500 hover:underline">删除</button>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <label className="text-xs text-soft">
                  问题占比 %
                  <Input type="number" min={1} max={100} value={rule.issue_pct} onChange={(e) => { const next = [...productRules]; next[idx] = { ...rule, issue_pct: Number(e.target.value) }; setProductRules(next); }} className="mt-0.5 rounded-card border-line text-sm" />
                </label>
                <label className="text-xs text-soft">
                  负面率 %
                  <Input type="number" min={1} max={100} value={rule.neg_rate} onChange={(e) => { const next = [...productRules]; next[idx] = { ...rule, neg_rate: Number(e.target.value) }; setProductRules(next); }} className="mt-0.5 rounded-card border-line text-sm" />
                </label>
                <label className="text-xs text-soft">
                  亮点占比 %
                  <Input type="number" min={1} max={100} value={rule.hl_pct} onChange={(e) => { const next = [...productRules]; next[idx] = { ...rule, hl_pct: Number(e.target.value) }; setProductRules(next); }} className="mt-0.5 rounded-card border-line text-sm" />
                </label>
              </div>
            </div>
          ))}
          <Button type="button" variant="outline" onClick={addProductRule} className="rounded-pill border-line px-4 py-2 text-sm">+ 添加产品</Button>
        </div>
      </section>

      {/* ④ 部门负责人 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">部门负责人</h2>
        <p className="mt-1 text-sm text-soft">配置后推送消息将 @对应负责人。Open ID 从飞书管理后台获取。</p>
        {smartLoading ? <div className="py-4 text-sm text-soft">加载中...</div> : (
          <div className="mt-4 space-y-2">
            {(Object.keys(DEPT_LABELS) as Array<keyof DeptContactSettings>).map((dept) => (
              <div key={dept} className="flex items-center gap-3">
                <span className="w-12 text-sm font-medium text-ink">{DEPT_LABELS[dept]}</span>
                <Input value={deptContacts[dept]} onChange={(e) => setDeptContacts({ ...deptContacts, [dept]: e.target.value })} placeholder={`ou_xxx`} className="flex-1 rounded-card border-line font-mono text-sm" />
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ⑤ 周期推送 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">周期推送</h2>
        {smartLoading ? <div className="py-4 text-sm text-soft">加载中...</div> : (
          <div className="mt-4 space-y-3">
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" checked={periodicPush.enabled} onChange={(e) => setPeriodicPush({ ...periodicPush, enabled: e.target.checked })} />
              启用周期推送
            </label>
            {periodicPush.enabled && (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <label className="text-xs text-soft">
                  频率
                  <select className="mt-0.5 w-full rounded-card border border-line px-2 py-1.5 text-sm" value={periodicPush.frequency} onChange={(e) => setPeriodicPush({ ...periodicPush, frequency: e.target.value as PeriodicPushSettings["frequency"] })}>
                    {FREQUENCY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </label>
                {(periodicPush.frequency === "weekly" || periodicPush.frequency === "biweekly") && (
                  <label className="text-xs text-soft">
                    推送日
                    <select className="mt-0.5 w-full rounded-card border border-line px-2 py-1.5 text-sm" value={periodicPush.day_of_week} onChange={(e) => setPeriodicPush({ ...periodicPush, day_of_week: e.target.value })}>
                      {DAY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </label>
                )}
                {periodicPush.frequency === "monthly" && (
                  <label className="text-xs text-soft">
                    每月几号
                    <Input type="number" min={1} max={28} value={periodicPush.day_of_month} onChange={(e) => setPeriodicPush({ ...periodicPush, day_of_month: parseInt(e.target.value) || 1 })} className="mt-0.5 rounded-card border-line text-sm" />
                  </label>
                )}
                <label className="text-xs text-soft">
                  时间
                  <Input type="time" value={periodicPush.time} onChange={(e) => setPeriodicPush({ ...periodicPush, time: e.target.value })} className="mt-0.5 rounded-card border-line text-sm" />
                </label>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ⑥ 升级规则 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">升级规则</h2>
        <p className="mt-1 text-sm text-soft">当某问题连续 N 个推送周期满足条件时，自动升级并生成行动建议。</p>
        {smartLoading ? <div className="py-4 text-sm text-soft">加载中...</div> : (
          <div className="mt-4 grid grid-cols-3 gap-3">
            <label className="text-xs text-soft">
              连续周期数
              <Input type="number" min={2} max={10} value={escalationRules.consecutive_count} onChange={(e) => setEscalationRules({ ...escalationRules, consecutive_count: parseInt(e.target.value) || 3 })} className="mt-0.5 rounded-card border-line text-sm" />
            </label>
            <label className="text-xs text-soft">
              TOP N 阈值
              <Input type="number" min={1} max={10} value={escalationRules.top_n} onChange={(e) => setEscalationRules({ ...escalationRules, top_n: parseInt(e.target.value) || 3 })} className="mt-0.5 rounded-card border-line text-sm" />
            </label>
            <label className="text-xs text-soft">
              占比阈值 %
              <Input type="number" min={1} max={50} step={0.5} value={escalationRules.pct_threshold} onChange={(e) => setEscalationRules({ ...escalationRules, pct_threshold: parseFloat(e.target.value) || 10 })} className="mt-0.5 rounded-card border-line text-sm" />
            </label>
          </div>
        )}
      </section>

      {/* 保存 */}
      <div className="sticky bottom-4 flex items-center gap-4 rounded-shell border border-line bg-white/95 p-4 shadow-card backdrop-blur">
        <Button type="button" onClick={handleSave} disabled={!canSave || isSaving} className="rounded-pill bg-ink px-6 py-2.5 text-sm font-semibold text-white shadow-card hover:bg-ink/90">
          {isSaving ? "保存中..." : "保存全部设置"}
        </Button>
        {error && <span className="text-sm text-red-600">{error}</span>}
        {message && <span className="text-sm text-green-700">{message}</span>}
      </div>
    </div>
  );
}

