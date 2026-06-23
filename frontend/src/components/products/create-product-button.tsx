"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Plus } from "lucide-react";

import { createProduct, type ProductCreatePayload } from "@/lib/api/browser";

const lifecycleOptions = [
  { value: "research", label: "调研期" },
  { value: "launch", label: "新品期" },
  { value: "growth", label: "成长期" },
  { value: "mature", label: "成熟期" },
  { value: "decline", label: "衰退期" },
];

const platformOptions = ["Amazon", "eBay", "Shopee", "AliExpress", "Walmart", "其他"];

export function CreateProductButton() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<ProductCreatePayload>({
    parent_product_id: "",
    name: "",
    platform: "Amazon",
    category: "",
    lifecycle_stage: "growth",
    current_version: "V1",
  });

  function updateField<K extends keyof ProductCreatePayload>(key: K, value: ProductCreatePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.parent_product_id.trim()) return;
    setSubmitting(true);
    try {
      await createProduct({
        ...form,
        parent_product_id: form.parent_product_id.trim(),
        name: form.name?.trim() || undefined,
        category: form.category?.trim() || undefined,
      });
      setOpen(false);
      setForm({
        parent_product_id: "",
        name: "",
        platform: "Amazon",
        category: "",
        lifecycle_stage: "growth",
        current_version: "V1",
      });
      router.refresh();
    } catch {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex min-h-11 items-center justify-center gap-2 rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:bg-ink/90"
      >
        <Plus className="h-4 w-4" />
        新建产品
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-lg rounded-shell border border-line bg-white p-6 shadow-card"
      >
        <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
          新建产品组
        </h3>

        <div className="mt-6 space-y-4">
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              产品 ID（必填）
            </label>
            <input
              type="text"
              value={form.parent_product_id}
              onChange={(e) => updateField("parent_product_id", e.target.value)}
              placeholder="如 ASIN / SKU 编号"
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
              required
            />
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              产品名称
            </label>
            <input
              type="text"
              value={form.name ?? ""}
              onChange={(e) => updateField("name", e.target.value)}
              placeholder="可选，便于识别"
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                平台
              </label>
              <select
                value={form.platform ?? "Amazon"}
                onChange={(e) => updateField("platform", e.target.value)}
                className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
              >
                {platformOptions.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                生命周期
              </label>
              <select
                value={form.lifecycle_stage ?? "growth"}
                onChange={(e) => updateField("lifecycle_stage", e.target.value)}
                className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
              >
                {lifecycleOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              类目
            </label>
            <input
              type="text"
              value={form.category ?? ""}
              onChange={(e) => updateField("category", e.target.value)}
              placeholder="如 电子配件、家居用品"
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </div>
        </div>

        <div className="mt-8 flex justify-end gap-3">
          <button
            type="button"
            onClick={() => setOpen(false)}
            disabled={submitting}
            className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-soft"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={submitting || !form.parent_product_id.trim()}
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card disabled:opacity-50"
          >
            {submitting ? "创建中…" : "创建"}
          </button>
        </div>
      </form>
    </div>
  );
}
