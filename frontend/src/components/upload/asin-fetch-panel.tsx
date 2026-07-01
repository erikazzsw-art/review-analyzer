"use client";

import React, { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchByAsin } from "@/lib/api/browser";
import { track } from "@/lib/analytics";

const PLATFORMS = [
  { value: "amazon", label: "Amazon" },
  { value: "aliexpress", label: "AliExpress" },
  { value: "shopee", label: "Shopee" },
  { value: "ebay", label: "eBay" },
  { value: "walmart", label: "Walmart" },
] as const;

const MARKETPLACES = [
  { value: "us", label: "Amazon US" },
  { value: "uk", label: "Amazon UK" },
  { value: "ca", label: "Amazon CA" },
  { value: "au", label: "Amazon AU" },
] as const;

const SHOPEE_REGIONS = [
  { value: "sg", label: "Shopee SG" },
  { value: "th", label: "Shopee TH" },
] as const;

const EBAY_MARKETS = [
  { value: "us", label: "eBay US" },
  { value: "uk", label: "eBay UK" },
] as const;

const WALMART_MARKETS = [
  { value: "us", label: "Walmart US" },
  { value: "ca", label: "Walmart CA" },
] as const;

type Platform = "amazon" | "aliexpress" | "shopee" | "ebay" | "walmart";

type FormState = {
  platform: Platform;
  productCode: string;
  marketplace: string;
  productName: string;
  fetchAllVariants: boolean;
};

const VALIDATION: Record<Platform, { pattern: RegExp; hint: string; placeholder: string; maxLength: number }> = {
  amazon: {
    pattern: /^[A-Z0-9]{10}$/,
    hint: "ASIN 必须为 10 位字母数字组合",
    placeholder: "例如：B0DFHB98KJ（ASIN）",
    maxLength: 10,
  },
  aliexpress: {
    pattern: /^\d{12,16}$/,
    hint: "Product ID 必须为 12-16 位数字",
    placeholder: "例如：1005006714526748（Product ID）",
    maxLength: 16,
  },
  shopee: {
    pattern: /^\d{5,15}\.\d{5,15}$/,
    hint: "格式：商品ID.店铺ID（如 23388006672.673355029）",
    placeholder: "例如：23388006672.673355029",
    maxLength: 31,
  },
  ebay: {
    pattern: /^\d{9,15}$/,
    hint: "eBay Item Number 必须为 9-15 位数字",
    placeholder: "例如：256218498498（Item Number）",
    maxLength: 15,
  },
  walmart: {
    pattern: /^[A-Za-z0-9]{6,13}$/,
    hint: "Walmart Product ID 必须为 6-13 位字母数字",
    placeholder: "例如：5127405080（Product ID）",
    maxLength: 13,
  },
};

export function AsinFetchPanel() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>({
    platform: "amazon",
    productCode: "",
    marketplace: "us",
    productName: "",
    fetchAllVariants: false,
  });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validation = VALIDATION[form.platform];
  const normalizedCode = form.platform === "amazon" || form.platform === "walmart" ? form.productCode.toUpperCase() : form.productCode;
  const isValidCode = useMemo(() => validation.pattern.test(normalizedCode), [normalizedCode, validation.pattern]);
  const canSubmit = isValidCode && !isSubmitting;

  async function handleSubmit() {
    if (!canSubmit) return;
    setError("");
    setIsSubmitting(true);
    track("asin_fetch_start", { asin: normalizedCode, platform: form.platform, marketplace: form.marketplace });

    try {
      const result = await fetchByAsin({
        asin: normalizedCode,
        platform: form.platform,
        marketplace: form.marketplace,
        productName: form.productName || undefined,
        fetchAllVariants: form.fetchAllVariants,
      });
      track("asin_fetch_queued", { job_id: result.job_id });
      router.push(`/analysis/results?job_id=${result.job_id}`);
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "评论拉取任务创建失败");
      track("asin_fetch_fail", { error: candidate.message || "unknown" });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* 平台选择器 */}
      <div className="flex gap-1 rounded-card border border-line p-1 w-fit">
        {PLATFORMS.map((p) => (
          <button
            key={p.value}
            type="button"
            onClick={() => setForm((c) => ({ ...c, platform: p.value, productCode: "", marketplace: p.value === "shopee" ? "sg" : "us" }))}
            className={`px-4 py-2 rounded-md text-sm font-medium transition ${
              form.platform === p.value
                ? "bg-ink text-white shadow-sm"
                : "text-ink/60 hover:text-ink hover:bg-gray-50"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">产品编码</span>
          <input
            value={form.productCode}
            onChange={(e) => {
              let val = e.target.value;
              if (form.platform === "amazon" || form.platform === "walmart") {
                val = val.toUpperCase().replace(/[^A-Z0-9]/g, "");
              } else if (form.platform === "shopee") {
                val = val.replace(/[^\d.]/g, "");
              } else {
                val = val.replace(/\D/g, "");
              }
              setForm((c) => ({ ...c, productCode: val }));
            }}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm font-mono outline-none transition focus:border-[#f36f8f]"
            placeholder={validation.placeholder}
            maxLength={validation.maxLength}
          />
          {form.productCode.length > 0 && !isValidCode && (
            <span className="text-xs text-[#c45863]">{validation.hint}</span>
          )}
        </label>

        {form.platform === "amazon" && (
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
        )}

        {form.platform === "shopee" && (
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">地区</span>
            <select
              value={form.marketplace}
              onChange={(e) => setForm((c) => ({ ...c, marketplace: e.target.value }))}
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            >
              {SHOPEE_REGIONS.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </label>
        )}

        {form.platform === "ebay" && (
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">站点</span>
            <select
              value={form.marketplace}
              onChange={(e) => setForm((c) => ({ ...c, marketplace: e.target.value }))}
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            >
              {EBAY_MARKETS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </label>
        )}

        {form.platform === "walmart" && (
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">站点</span>
            <select
              value={form.marketplace}
              onChange={(e) => setForm((c) => ({ ...c, marketplace: e.target.value }))}
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            >
              {WALMART_MARKETS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </label>
        )}

        <label className={`space-y-2 ${form.platform !== "aliexpress" ? "md:col-span-2" : ""}`}>
          <span className="text-sm font-semibold text-ink">产品名称（可选）</span>
          <input
            value={form.productName}
            onChange={(e) => setForm((c) => ({ ...c, productName: e.target.value }))}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            placeholder={form.platform === "amazon" ? "留空则自动从 Amazon 获取" : "留空则使用 Product ID 标识"}
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
            {form.platform === "amazon"
              ? "抓取所有变体（自动识别同款所有子 ASIN 并合并分析）"
              : form.platform === "shopee"
                ? "抓取所有星级评论（含 1-5 星全覆盖）"
                : "抓取所有 SKU 变体评论（按 SKU 标签分类）"}
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
