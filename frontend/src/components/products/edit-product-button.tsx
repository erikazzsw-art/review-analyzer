"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Pencil } from "lucide-react";

import { updateProduct, type ProductUpdatePayload } from "@/lib/api/browser";

const lifecycleOptions = [
  { value: "research", label: "调研期" },
  { value: "launch", label: "新品期" },
  { value: "growth", label: "成长期" },
  { value: "mature", label: "成熟期" },
  { value: "decline", label: "衰退期" },
];

const platformOptions = ["Amazon", "eBay", "Shopee", "AliExpress", "Walmart", "其他"];

type EditProductButtonProps = {
  productId: number;
  initial: {
    name?: string;
    platform?: string;
    category?: string;
    lifecycle_stage?: string;
    current_version?: string;
    core_selling_points?: string;
    main_competitors?: string;
    owner_role?: string;
    production_cycle_days?: number;
  };
};

export function EditProductButton({ productId, initial }: EditProductButtonProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<ProductUpdatePayload>({
    name: initial.name ?? "",
    platform: initial.platform ?? "Amazon",
    category: initial.category ?? "",
    lifecycle_stage: initial.lifecycle_stage ?? "growth",
    current_version: initial.current_version ?? "V1",
    core_selling_points: initial.core_selling_points ?? "",
    main_competitors: initial.main_competitors ?? "",
  });

  function updateField<K extends keyof ProductUpdatePayload>(key: K, value: ProductUpdatePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload: ProductUpdatePayload = {};
      if (form.name?.trim()) payload.name = form.name.trim();
      if (form.platform) payload.platform = form.platform;
      if (form.category?.trim()) payload.category = form.category.trim();
      if (form.lifecycle_stage) payload.lifecycle_stage = form.lifecycle_stage;
      if (form.current_version?.trim()) payload.current_version = form.current_version.trim();
      if (form.core_selling_points?.trim()) payload.core_selling_points = form.core_selling_points.trim();
      if (form.main_competitors?.trim()) payload.main_competitors = form.main_competitors.trim();
      await updateProduct(productId, payload);
      setOpen(false);
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
        className="inline-flex min-h-9 items-center justify-center gap-1.5 rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-ink transition hover:border-ink/30"
      >
        <Pencil className="h-3.5 w-3.5" />
        编辑
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
          编辑产品
        </h3>

        <div className="mt-6 space-y-4">
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              产品名称
            </label>
            <input
              type="text"
              value={form.name ?? ""}
              onChange={(e) => updateField("name", e.target.value)}
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
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              核心卖点
            </label>
            <textarea
              value={form.core_selling_points ?? ""}
              onChange={(e) => updateField("core_selling_points", e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              主要竞品
            </label>
            <textarea
              value={form.main_competitors ?? ""}
              onChange={(e) => updateField("main_competitors", e.target.value)}
              rows={2}
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
            disabled={submitting}
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card disabled:opacity-50"
          >
            {submitting ? "保存中…" : "保存"}
          </button>
        </div>
      </form>
    </div>
  );
}
