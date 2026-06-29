"use client";

import React, { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchByAsin } from "@/lib/api/browser";
import { track } from "@/lib/analytics";

const MARKETPLACES = [
  { value: "us", label: "Amazon US" },
  { value: "uk", label: "Amazon UK" },
  { value: "de", label: "Amazon DE" },
  { value: "fr", label: "Amazon FR" },
  { value: "jp", label: "Amazon JP" },
  { value: "ca", label: "Amazon CA" },
  { value: "it", label: "Amazon IT" },
  { value: "es", label: "Amazon ES" },
  { value: "au", label: "Amazon AU" },
] as const;

type AsinFormState = {
  asin: string;
  marketplace: string;
  productName: string;
  fetchAllVariants: boolean;
};

export function AsinFetchPanel() {
  const router = useRouter();
  const [form, setForm] = useState<AsinFormState>({
    asin: "",
    marketplace: "us",
    productName: "",
    fetchAllVariants: false,
  });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isValidAsin = useMemo(() => /^[A-Z0-9]{10}$/.test(form.asin.toUpperCase()), [form.asin]);
  const canSubmit = isValidAsin && !isSubmitting;

  async function handleSubmit() {
    if (!canSubmit) return;
    setError("");
    setIsSubmitting(true);
    track("asin_fetch_start", { asin: form.asin, marketplace: form.marketplace });

    try {
      const result = await fetchByAsin({
        asin: form.asin.toUpperCase(),
        marketplace: form.marketplace,
        productName: form.productName || undefined,
        fetchAllVariants: form.fetchAllVariants,
      });
      track("asin_fetch_queued", { job_id: result.job_id });
      router.push(`/analysis/results?job_id=${result.job_id}`);
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "ASIN 拉取任务创建失败");
      track("asin_fetch_fail", { error: candidate.message || "unknown" });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">ASIN</span>
          <input
            value={form.asin}
            onChange={(e) => setForm((c) => ({ ...c, asin: e.target.value.toUpperCase() }))}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm font-mono outline-none transition focus:border-[#f36f8f]"
            placeholder="例如：B0DFHB98KJ"
            maxLength={10}
          />
          {form.asin.length > 0 && !isValidAsin && (
            <span className="text-xs text-[#c45863]">ASIN 必须为 10 位字母数字组合</span>
          )}
        </label>
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">站点</span>
          <select
            value={form.marketplace}
            onChange={(e) => setForm((c) => ({ ...c, marketplace: e.target.value }))}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          >
            {MARKETPLACES.map((mp) => (
              <option key={mp.value} value={mp.value}>{mp.label}</option>
            ))}
          </select>
        </label>
        <label className="space-y-2 md:col-span-2">
          <span className="text-sm font-semibold text-ink">产品名称（可选）</span>
          <input
            value={form.productName}
            onChange={(e) => setForm((c) => ({ ...c, productName: e.target.value }))}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            placeholder="留空则自动从 Amazon 获取"
          />
        </label>
        <label className="flex items-center gap-3 md:col-span-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={form.fetchAllVariants}
            onChange={(e) => setForm((c) => ({ ...c, fetchAllVariants: e.target.checked }))}
            className="h-4 w-4 rounded border-line text-[#f36f8f] accent-[#f36f8f]"
          />
          <span className="text-sm text-ink/80">
            抓取所有变体（自动识别同款所有子 ASIN 并合并分析）
          </span>
        </label>
      </div>

      {error && (
        <div className="rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]">
          {error}
        </div>
      )}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="inline-flex min-h-12 items-center justify-center rounded-pill bg-ink px-6 py-3 text-sm font-semibold text-white shadow-card transition disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "提交中..." : "拉取评论并分析"}
      </button>
    </div>
  );
}
