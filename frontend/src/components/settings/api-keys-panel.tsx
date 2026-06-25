"use client";

import { useState } from "react";

import { saveSettings } from "@/lib/api/browser";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Props = { initialApiKey: string };

export function ApiKeysPanel({ initialApiKey }: Props) {
  const [apiKey, setApiKey] = useState(initialApiKey);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function handleSave() {
    setError(""); setMessage(""); setIsSaving(true);
    try {
      await saveSettings({ webhookUrl: "", webhookSecret: "", webhookGroupName: "", apiKey: apiKey.trim(), rules: {} as never, productRules: [] });
      setMessage("API Key 已保存。");
    } catch (err) {
      setError((err as { message?: string }).message || "保存失败");
    } finally { setIsSaving(false); }
  }

  return (
    <div>
      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card">
        <h2 className="font-heading text-2xl font-extrabold tracking-tight text-ink">API 密钥</h2>
        <p className="mt-1 text-sm text-soft">DeepSeek API Key 用于 AI 分析功能。密钥会加密存储，不会明文显示。</p>
        <div className="mt-5 space-y-4">
          <label className="block space-y-1">
            <span className="text-sm font-semibold text-ink">DeepSeek API Key</span>
            <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-..." className="rounded-card border-line" />
          </label>
          <div className="flex items-center gap-4">
            <Button type="button" onClick={handleSave} disabled={isSaving} className="rounded-pill bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-card hover:bg-ink/90">
              {isSaving ? "保存中..." : "保存"}
            </Button>
            {error && <span className="text-sm text-red-600">{error}</span>}
            {message && <span className="text-sm text-green-700">{message}</span>}
          </div>
        </div>
      </section>
    </div>
  );
}
