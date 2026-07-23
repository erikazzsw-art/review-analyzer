"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { fetchSmartPushSettings, saveSettings, saveSmartPushSettings, testWebhook } from "@/lib/api/browser";
import type {
  DeptContactSettings,
  EscalationRuleSettings,
  PeriodicPushSettings,
  ProductRuleSettings,
  PushRuleSettings,
  SettingsResponse,
  WebhookPlatform,
} from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProductSearchCombobox } from "@/components/analysis/product-search-combobox";

type Props = { initialSettings: SettingsResponse };

const DEPT_KEYS = ["qa", "product", "ops", "cs", "other"] as const;
const FREQUENCY_VALUES = ["daily", "weekly", "biweekly", "monthly"] as const;
const DAY_VALUES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] as const;
const PLATFORM_VALUES: WebhookPlatform[] = ["feishu", "dingtalk", "wechat"];

const PLATFORM_META: Record<WebhookPlatform, { showSecret: boolean; metaKey: "platformFeishu" | "platformDingtalk" | "platformWechat" }> = {
  feishu: { showSecret: true, metaKey: "platformFeishu" },
  dingtalk: { showSecret: true, metaKey: "platformDingtalk" },
  wechat: { showSecret: false, metaKey: "platformWechat" },
};

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
  const t = useTranslations("settings.push");
  const [webhookPlatform, setWebhookPlatform] = useState<WebhookPlatform>(initialSettings.webhook_platform ?? "feishu");
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

  const platformMeta = PLATFORM_META[webhookPlatform];
  const platformKey = platformMeta.metaKey;

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

  async function handleSave() {
    setError(""); setMessage(""); setIsSaving(true);
    try {
      await saveSettings({
        webhookPlatform,
        webhookUrl: webhookUrl.trim(),
        webhookSecret: webhookSecret.trim(),
        webhookGroupName: webhookGroupName.trim(),
        apiKey: "",
        rules,
        productRules,
      });
      await saveSmartPushSettings({ periodic_push: periodicPush, dept_contacts: deptContacts, escalation_rules: escalationRules, dept_mapping: [] });
      setMessage(t("saveSuccess"));
    } catch (err) {
      setError((err as { message?: string }).message || t("saveFail"));
    } finally { setIsSaving(false); }
  }

  async function handleTestWebhook() {
    setError(""); setMessage(""); setIsTesting(true);
    try {
      const result = await testWebhook({
        webhookPlatform,
        webhookUrl: webhookUrl.trim(),
        webhookSecret: webhookSecret.trim(),
      });
      if (result.ok) {
        setMessage((result.msg as string) || t("testSuccess"));
      } else {
        setError((result.msg as string) || t("testFallback"));
      }
    } catch (err) {
      setError((err as { message?: string }).message || t("testFail"));
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
      {/* ① 绑定推送渠道 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">{t(`${platformKey}.sectionTitle`)}</h2>
        <p className="mt-1 text-sm text-soft">{t(`${platformKey}.sectionDesc`)}</p>
        <div className="mt-5 space-y-4">
          <label className="block space-y-1">
            <span className="text-sm font-semibold text-ink">{t("form.platformLabel")}</span>
            <select
              value={webhookPlatform}
              onChange={(e) => setWebhookPlatform(e.target.value as WebhookPlatform)}
              className="w-full rounded-card border border-line bg-white px-3 py-2 text-sm"
            >
              {PLATFORM_VALUES.map((value) => (
                <option key={value} value={value}>{t(`platformLabel.${value}`)}</option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-sm font-semibold text-ink">{t("form.webhookUrlLabel")}</span>
            <Input value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} placeholder={t(`${platformKey}.urlPlaceholder`)} className="rounded-card border-line" />
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            {platformMeta.showSecret ? (
              <label className="block space-y-1">
                <span className="text-sm font-semibold text-ink">{t(`${platformKey}.secretHint`)}</span>
                <Input type="password" value={webhookSecret} onChange={(e) => setWebhookSecret(e.target.value)} placeholder={t(`${platformKey}.secretPlaceholder`)} className="rounded-card border-line" />
              </label>
            ) : (
              <div className="text-xs text-soft self-center">{t("wechatNoSecretHint")}</div>
            )}
            <label className="block space-y-1">
              <span className="text-sm font-semibold text-ink">{t("form.webhookGroupNameLabel")}</span>
              <Input value={webhookGroupName} onChange={(e) => setWebhookGroupName(e.target.value)} className="rounded-card border-line" />
            </label>
          </div>
          <Button type="button" variant="outline" onClick={handleTestWebhook} disabled={isTesting} className="rounded-pill border-line px-5 py-2 text-sm font-semibold">
            {isTesting ? t("form.testBtnLoading") : t("form.testBtn")}
          </Button>
        </div>
      </section>

      {/* ② 全局触发规则 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">{t("globalRules.title")}</h2>
        <p className="mt-1 text-sm text-soft">{t("globalRules.desc")}</p>
        <div className="mt-4 space-y-3">
          <RuleToggle label={t("globalRules.issuePct")} checked={rules.issue_pct_enabled} value={rules.issue_pct_threshold} onToggle={(v) => updateRule("issue_pct_enabled", v)} onValue={(v) => updateRule("issue_pct_threshold", v)} />
          <RuleToggle label={t("globalRules.negRate")} checked={rules.neg_rate_enabled} value={rules.neg_rate_threshold} onToggle={(v) => updateRule("neg_rate_enabled", v)} onValue={(v) => updateRule("neg_rate_threshold", v)} />
          <RuleToggle label={t("globalRules.negRateCompare")} checked={rules.neg_rate_compare_enabled} value={rules.neg_rate_compare_threshold} onToggle={(v) => updateRule("neg_rate_compare_enabled", v)} onValue={(v) => updateRule("neg_rate_compare_threshold", v)} />
          <RuleToggle label={t("globalRules.issueCompare")} checked={rules.issue_compare_enabled} value={rules.issue_compare_threshold} onToggle={(v) => updateRule("issue_compare_enabled", v)} onValue={(v) => updateRule("issue_compare_threshold", v)} />
          <RuleToggle label={t("globalRules.highlightPct")} checked={rules.highlight_pct_enabled} value={rules.highlight_pct_threshold} onToggle={(v) => updateRule("highlight_pct_enabled", v)} onValue={(v) => updateRule("highlight_pct_threshold", v)} />
          <RuleToggle label={t("globalRules.highlightCompare")} checked={rules.highlight_compare_enabled} value={rules.highlight_compare_threshold} onToggle={(v) => updateRule("highlight_compare_enabled", v)} onValue={(v) => updateRule("highlight_compare_threshold", v)} />
          <label className="flex items-center gap-3 rounded-card border border-line bg-white px-4 py-3 text-sm text-ink">
            <input type="checkbox" checked={rules.auto_push_new_batch} onChange={(e) => updateRule("auto_push_new_batch", e.target.checked)} />
            {t("globalRules.autoPushNewBatch")}
          </label>
        </div>
      </section>

      {/* ③ 产品级专项规则 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">{t("productRules.title")}</h2>
        <p className="mt-1 text-sm text-soft">{t("productRules.desc")}</p>
        <div className="mt-4 space-y-3">
          {productRules.map((rule, idx) => (
            <div key={idx} className="rounded-card border border-line bg-white p-4 space-y-2">
              <div className="flex items-center gap-2">
                <div className="flex-1 min-w-0">
                  <ProductSearchCombobox value={rule.product_id} onChange={(pid) => { const next = [...productRules]; next[idx] = { ...rule, product_id: pid }; setProductRules(next); }} placeholder={t("productRules.productIdPlaceholder")} />
                </div>
                <label className="flex items-center gap-1 text-xs text-soft">
                  <input type="checkbox" checked={rule.enabled} onChange={(e) => { const next = [...productRules]; next[idx] = { ...rule, enabled: e.target.checked }; setProductRules(next); }} />
                  {t("productRules.enabledLabel")}
                </label>
                <button type="button" onClick={() => removeProductRule(idx)} className="text-xs text-red-500 hover:underline">{t("productRules.deleteBtn")}</button>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <label className="text-xs text-soft">
                  {t("productRules.issuePctLabel")}
                  <Input type="number" min={1} max={100} value={rule.issue_pct} onChange={(e) => { const next = [...productRules]; next[idx] = { ...rule, issue_pct: Number(e.target.value) }; setProductRules(next); }} className="mt-0.5 rounded-card border-line text-sm" />
                </label>
                <label className="text-xs text-soft">
                  {t("productRules.negRateLabel")}
                  <Input type="number" min={1} max={100} value={rule.neg_rate} onChange={(e) => { const next = [...productRules]; next[idx] = { ...rule, neg_rate: Number(e.target.value) }; setProductRules(next); }} className="mt-0.5 rounded-card border-line text-sm" />
                </label>
                <label className="text-xs text-soft">
                  {t("productRules.hlPctLabel")}
                  <Input type="number" min={1} max={100} value={rule.hl_pct} onChange={(e) => { const next = [...productRules]; next[idx] = { ...rule, hl_pct: Number(e.target.value) }; setProductRules(next); }} className="mt-0.5 rounded-card border-line text-sm" />
                </label>
              </div>
            </div>
          ))}
          <Button type="button" variant="outline" onClick={addProductRule} className="rounded-pill border-line px-4 py-2 text-sm">{t("productRules.addBtn")}</Button>
        </div>
      </section>

      {/* ④ 负责人 Open ID */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">{t("deptContacts.title")}</h2>
        <p className="mt-1 text-sm text-soft">{t(`${platformKey}.contactHint`)}</p>
        <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <div>
            <p className="font-semibold text-ink">{t("deptContacts.productOwnerTitle")}</p>
            <p className="mt-1 leading-6 text-soft">{t("deptContacts.productOwnerDesc")}</p>
          </div>
          <div>
            <p className="font-semibold text-ink">{t("deptContacts.issueOwnerTitle")}</p>
            <p className="mt-1 leading-6 text-soft">{t("deptContacts.issueOwnerDesc")}</p>
          </div>
        </div>
        <p className="mt-3 text-xs leading-5 text-soft">{t("deptContacts.futureMappingNote")}</p>
        {smartLoading ? <div className="py-4 text-sm text-soft">{t("loading")}</div> : (
          <div className="mt-4 space-y-3">
            {DEPT_KEYS.map((dept) => (
              <div key={dept} className="grid gap-2 md:grid-cols-[160px_1fr] md:items-center">
                <span className="text-sm font-medium text-ink">
                  {t(`deptLabel.${dept}`)}
                  <span className="block text-xs font-normal leading-5 text-soft">{t(`deptContactHint.${dept}`)}</span>
                </span>
                <Input
                  value={deptContacts[dept]}
                  onChange={(e) => setDeptContacts({ ...deptContacts, [dept]: e.target.value })}
                  placeholder={t(`${platformKey}.contactPlaceholder`)}
                  disabled={webhookPlatform !== "feishu"}
                  className="flex-1 rounded-card border-line font-mono text-sm disabled:bg-slate-50 disabled:text-soft"
                />
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ⑤ 周期推送 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">{t("periodic.title")}</h2>
        {smartLoading ? <div className="py-4 text-sm text-soft">{t("loading")}</div> : (
          <div className="mt-4 space-y-3">
            <label className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" checked={periodicPush.enabled} onChange={(e) => setPeriodicPush({ ...periodicPush, enabled: e.target.checked })} />
              {t("periodic.enableLabel")}
            </label>
            {periodicPush.enabled && (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <label className="text-xs text-soft">
                  {t("periodic.frequencyLabel")}
                  <select className="mt-0.5 w-full rounded-card border border-line px-2 py-1.5 text-sm" value={periodicPush.frequency} onChange={(e) => setPeriodicPush({ ...periodicPush, frequency: e.target.value as PeriodicPushSettings["frequency"] })}>
                    {FREQUENCY_VALUES.map((value) => <option key={value} value={value}>{t(`frequencyLabel.${value}`)}</option>)}
                  </select>
                </label>
                {(periodicPush.frequency === "weekly" || periodicPush.frequency === "biweekly") && (
                  <label className="text-xs text-soft">
                    {t("periodic.dayOfWeekLabel")}
                    <select className="mt-0.5 w-full rounded-card border border-line px-2 py-1.5 text-sm" value={periodicPush.day_of_week} onChange={(e) => setPeriodicPush({ ...periodicPush, day_of_week: e.target.value })}>
                      {DAY_VALUES.map((value) => <option key={value} value={value}>{t(`dayOfWeekLabel.${value}`)}</option>)}
                    </select>
                  </label>
                )}
                {periodicPush.frequency === "monthly" && (
                  <label className="text-xs text-soft">
                    {t("periodic.dayOfMonthLabel")}
                    <Input type="number" min={1} max={28} value={periodicPush.day_of_month} onChange={(e) => setPeriodicPush({ ...periodicPush, day_of_month: parseInt(e.target.value) || 1 })} className="mt-0.5 rounded-card border-line text-sm" />
                  </label>
                )}
                <label className="text-xs text-soft">
                  {t("periodic.timeLabel")}
                  <Input type="time" value={periodicPush.time} onChange={(e) => setPeriodicPush({ ...periodicPush, time: e.target.value })} className="mt-0.5 rounded-card border-line text-sm" />
                </label>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ⑥ 升级规则 */}
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">{t("escalation.title")}</h2>
        <p className="mt-1 text-sm text-soft">{t("escalation.desc")}</p>
        {smartLoading ? <div className="py-4 text-sm text-soft">{t("loading")}</div> : (
          <div className="mt-4 grid grid-cols-3 gap-3">
            <label className="text-xs text-soft">
              {t("escalation.consecutiveCount")}
              <Input type="number" min={2} max={10} value={escalationRules.consecutive_count} onChange={(e) => setEscalationRules({ ...escalationRules, consecutive_count: parseInt(e.target.value) || 3 })} className="mt-0.5 rounded-card border-line text-sm" />
            </label>
            <label className="text-xs text-soft">
              {t("escalation.topN")}
              <Input type="number" min={1} max={10} value={escalationRules.top_n} onChange={(e) => setEscalationRules({ ...escalationRules, top_n: parseInt(e.target.value) || 3 })} className="mt-0.5 rounded-card border-line text-sm" />
            </label>
            <label className="text-xs text-soft">
              {t("escalation.pctThreshold")}
              <Input type="number" min={1} max={50} step={0.5} value={escalationRules.pct_threshold} onChange={(e) => setEscalationRules({ ...escalationRules, pct_threshold: parseFloat(e.target.value) || 10 })} className="mt-0.5 rounded-card border-line text-sm" />
            </label>
          </div>
        )}
      </section>

      {/* 保存 */}
      <div className="sticky bottom-4 flex items-center gap-4 rounded-shell border border-line bg-white/95 p-4 shadow-card backdrop-blur">
        <Button type="button" onClick={handleSave} disabled={!canSave || isSaving} className="rounded-pill bg-ink px-6 py-2.5 text-sm font-semibold text-white shadow-card hover:bg-ink/90">
          {isSaving ? t("saveAllBtnLoading") : t("saveAllBtn")}
        </Button>
        {error && <span className="text-sm text-red-600">{error}</span>}
        {message && <span className="text-sm text-green-700">{message}</span>}
      </div>
    </div>
  );
}
