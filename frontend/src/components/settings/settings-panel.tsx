"use client";

import { useMemo, useRef, useState } from "react";

import { createBillingCheckout, saveSettings, testWebhook } from "@/lib/api/browser";
import type { ProductRuleSettings, PushRuleSettings, SettingsResponse } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type SettingsPanelProps = {
  initialSettings: SettingsResponse;
};

function cloneRules(rules: PushRuleSettings): PushRuleSettings {
  return { ...rules };
}

export function SettingsPanel({ initialSettings }: SettingsPanelProps) {
  const [webhookUrl, setWebhookUrl] = useState(initialSettings.webhook_url);
  const [webhookSecret, setWebhookSecret] = useState(initialSettings.webhook_secret);
  const [webhookGroupName, setWebhookGroupName] = useState(initialSettings.webhook_group_name);
  const [apiKey, setApiKey] = useState(initialSettings.api_key);
  const [rules, setRules] = useState<PushRuleSettings>(cloneRules(initialSettings.rules));
  const [productRules, setProductRules] = useState<ProductRuleSettings[]>(initialSettings.product_rules);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isCheckouting, setIsCheckouting] = useState(false);
  const checkoutContainerRef = useRef<HTMLDivElement | null>(null);

  const configured = Boolean(initialSettings.billing.configured);

  const canSave = useMemo(
    () => webhookUrl.trim().length > 0 || webhookSecret.trim().length >= 0 || apiKey.trim().length >= 0,
    [webhookUrl, webhookSecret, apiKey],
  );

  function updateRule<K extends keyof PushRuleSettings>(key: K, value: PushRuleSettings[K]): void {
    setRules((current) => ({ ...current, [key]: value }));
  }

  async function handleSave(): Promise<void> {
    setError("");
    setMessage("");
    setIsSaving(true);
    try {
      await saveSettings({
        webhookUrl: webhookUrl.trim(),
        webhookSecret: webhookSecret.trim(),
        webhookGroupName: webhookGroupName.trim(),
        apiKey: apiKey.trim(),
        rules,
        productRules,
      });
      setMessage("设置已保存。");
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "保存失败");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleTestWebhook(): Promise<void> {
    setError("");
    setMessage("");
    setIsTesting(true);
    try {
      const result = await testWebhook({
        webhookUrl: webhookUrl.trim(),
        webhookSecret: webhookSecret.trim(),
      });
      setMessage((result.message as string) || "连接测试完成。");
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "测试失败");
    } finally {
      setIsTesting(false);
    }
  }

  async function handleCheckout(): Promise<void> {
    setError("");
    setMessage("");
    setIsCheckouting(true);
    try {
      const result = await createBillingCheckout();
      if (!result.checkout_html) {
        setMessage(result.configured ? "Paddle 已配置，但未返回 checkout 内容。" : "Paddle 还未完全配置，请先检查环境变量。");
        return;
      }

      if (checkoutContainerRef.current) {
        checkoutContainerRef.current.innerHTML = result.checkout_html;
        const scripts = Array.from(checkoutContainerRef.current.querySelectorAll("script"));
        for (const script of scripts) {
          await new Promise<void>((resolve, reject) => {
            const next = document.createElement("script");
            Array.from(script.attributes).forEach((attribute) => {
              next.setAttribute(attribute.name, attribute.value);
            });
            const isExternal = Boolean(next.src);
            if (isExternal) {
              next.onload = () => resolve();
              next.onerror = () => reject(new Error("加载 Paddle 脚本失败"));
            } else {
              next.text = script.textContent || "";
              resolve();
            }
            script.replaceWith(next);
          });
        }
      }

      setMessage(result.configured ? "Paddle checkout 已打开。" : "Paddle 还未完全配置，请先检查环境变量。");
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "发起升级失败");
    } finally {
      setIsCheckouting(false);
    }
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
      <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
          SETTINGS
        </div>

        <div ref={checkoutContainerRef} className="hidden" aria-hidden="true" />
        <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          推送、密钥和规则
        </h2>
        <p className="mt-3 text-sm leading-7 text-soft">
          这里集中配置飞书 Webhook、DeepSeek API Key 和自动推送规则。保存后会直接写回后端。
        </p>

        <div className="mt-6 space-y-4">
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">飞书 Webhook</span>
            <Input
              value={webhookUrl}
              onChange={(event) => setWebhookUrl(event.target.value)}
              className="rounded-card border-line bg-white text-sm focus-visible:ring-rose/20 focus-visible:border-rose"
              placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
            />
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block space-y-2">
              <span className="text-sm font-semibold text-ink">加签密钥</span>
              <Input
                type="password"
                value={webhookSecret}
                onChange={(event) => setWebhookSecret(event.target.value)}
                className="rounded-card border-line bg-white text-sm focus-visible:ring-rose/20 focus-visible:border-rose"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-semibold text-ink">群名称备注</span>
              <Input
                value={webhookGroupName}
                onChange={(event) => setWebhookGroupName(event.target.value)}
                className="rounded-card border-line bg-white text-sm focus-visible:ring-rose/20 focus-visible:border-rose"
              />
            </label>
          </div>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">DeepSeek API Key</span>
            <Input
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              className="rounded-card border-line bg-white text-sm focus-visible:ring-rose/20 focus-visible:border-rose"
              placeholder="sk-..."
            />
          </label>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <Button
            type="button"
            variant="outline"
            onClick={handleTestWebhook}
            disabled={isTesting}
            className="min-h-11 rounded-pill border-line px-5 py-3 text-sm font-semibold text-ink"
          >
            {isTesting ? "测试中..." : "测试连接"}
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={!canSave || isSaving}
            className="min-h-11 rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-ink/90"
          >
            {isSaving ? "保存中..." : "保存设置"}
          </Button>
          <Button
            type="button"
            onClick={handleCheckout}
            disabled={isCheckouting}
            className="min-h-11 rounded-pill bg-rose px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-rose/90"
          >
            {isCheckouting ? "拉起支付..." : "升级到 Pro"}
          </Button>
        </div>

        {error ? (
          <div className="mt-4 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]">
            {error}
          </div>
        ) : null}
        {message ? (
          <div className="mt-4 rounded-card border border-[#c9e8dc] bg-[#f6fffb] px-4 py-3 text-sm leading-7 text-[#3d8b74]">
            {message}
          </div>
        ) : null}

        <div className="mt-8 space-y-4">
          <div className="text-sm font-semibold text-ink">自动推送规则</div>
          <RuleToggle
            label="问题占比阈值"
            checked={rules.issue_pct_enabled}
            value={rules.issue_pct_threshold}
            onToggle={(checked) => updateRule("issue_pct_enabled", checked)}
            onValue={(value) => updateRule("issue_pct_threshold", value)}
          />
          <RuleToggle
            label="负面率阈值"
            checked={rules.neg_rate_enabled}
            value={rules.neg_rate_threshold}
            onToggle={(checked) => updateRule("neg_rate_enabled", checked)}
            onValue={(value) => updateRule("neg_rate_threshold", value)}
          />
          <RuleToggle
            label="负面率环比"
            checked={rules.neg_rate_compare_enabled}
            value={rules.neg_rate_compare_threshold}
            onToggle={(checked) => updateRule("neg_rate_compare_enabled", checked)}
            onValue={(value) => updateRule("neg_rate_compare_threshold", value)}
          />
          <RuleToggle
            label="问题环比"
            checked={rules.issue_compare_enabled}
            value={rules.issue_compare_threshold}
            onToggle={(checked) => updateRule("issue_compare_enabled", checked)}
            onValue={(value) => updateRule("issue_compare_threshold", value)}
          />
          <RuleToggle
            label="亮点阈值"
            checked={rules.highlight_pct_enabled}
            value={rules.highlight_pct_threshold}
            onToggle={(checked) => updateRule("highlight_pct_enabled", checked)}
            onValue={(value) => updateRule("highlight_pct_threshold", value)}
          />
          <RuleToggle
            label="亮点环比"
            checked={rules.highlight_compare_enabled}
            value={rules.highlight_compare_threshold}
            onToggle={(checked) => updateRule("highlight_compare_enabled", checked)}
            onValue={(value) => updateRule("highlight_compare_threshold", value)}
          />
          <label className="flex items-center gap-3 rounded-card border border-line bg-white px-4 py-4 text-sm text-ink">
            <input
              type="checkbox"
              checked={rules.auto_push_new_batch}
              onChange={(event) => updateRule("auto_push_new_batch", event.target.checked)}
            />
            新批次自动推送
          </label>
        </div>
      </div>

      <div className="space-y-6">
        <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            PRODUCT RULES
          </div>
          <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            产品级规则
          </h3>
          <div className="mt-4 space-y-3">
            {productRules.length > 0 ? (
              productRules.map((rule, index) => (
                <div key={`${rule.product_id}-${index}`} className="rounded-card border border-line bg-white px-4 py-4 text-sm leading-7 text-ink">
                  <div className="font-semibold">{rule.product_id}</div>
                  <div className="mt-1 text-soft">
                    问题 {rule.issue_pct}% · 负面 {rule.neg_rate}% · 亮点 {rule.hl_pct}% · {rule.enabled ? "启用" : "停用"}
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
                暂无产品级规则。
              </div>
            )}
          </div>
        </section>

        <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            PREVIEW
          </div>
          <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            保存后的行为
          </h3>
          <p className="mt-3 text-sm leading-7 text-soft">
            这里保存的是飞书推送规则和 API Key；升级按钮会拉起 Paddle checkout，Webhook 会回写用户订阅计划。
          </p>
        </section>
      </div>
    </section>
  );
}

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
    <div className="grid gap-3 rounded-card border border-line bg-white px-4 py-4 md:grid-cols-[1fr_120px]">
      <label className="flex items-center gap-3 text-sm font-semibold text-ink">
        <input type="checkbox" checked={checked} onChange={(event) => onToggle(event.target.checked)} />
        {label}
      </label>
      <Input
        type="number"
        value={value}
        min={1}
        max={100}
        onChange={(event) => onValue(Number(event.target.value || 0))}
        className="rounded-card border-line bg-white text-sm"
      />
    </div>
  );
}
