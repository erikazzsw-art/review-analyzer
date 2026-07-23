"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";

import { createProduct, type ProductCreatePayload } from "@/lib/api/browser";

const lifecycleKeys = [
  { value: "research", key: "lifecycleResearch" },
  { value: "launch", key: "lifecycleLaunch" },
  { value: "growth", key: "lifecycleGrowth" },
  { value: "mature", key: "lifecycleMature" },
  { value: "decline", key: "lifecycleDecline" },
] as const;

const platformOptions = ["Amazon", "eBay", "Shopee", "AliExpress", "Walmart"];

export function CreateProductButton() {
  const t = useTranslations("products.create");
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<ProductCreatePayload>({
    parent_product_id: "",
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
    const productName = form.parent_product_id.trim();
    if (!productName) return;
    setSubmitting(true);
    try {
      await createProduct({
        ...form,
        parent_product_id: productName,
        name: productName,
        category: form.category?.trim() || undefined,
      });
      setOpen(false);
      setForm({
        parent_product_id: "",
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
        {t("createButton")}
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
          {t("createTitle")}
        </h3>

        <div className="mt-6 space-y-4">
          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("productNameLabel")}
            </label>
            <input
              type="text"
              value={form.parent_product_id}
              onChange={(e) => updateField("parent_product_id", e.target.value)}
              placeholder={t("productNamePlaceholder")}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
              required
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                {t("platformLabel")}
              </label>
              <select
                value={form.platform ?? "Amazon"}
                onChange={(e) => updateField("platform", e.target.value)}
                className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
              >
                {platformOptions.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
                <option value="其他">{t("platformOther")}</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                {t("lifecycleLabel")}
              </label>
              <select
                value={form.lifecycle_stage ?? "growth"}
                onChange={(e) => updateField("lifecycle_stage", e.target.value)}
                className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
              >
                {lifecycleKeys.map((opt) => (
                  <option key={opt.value} value={opt.value}>{t(opt.key)}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("categoryLabel")}
            </label>
            <input
              type="text"
              value={form.category ?? ""}
              onChange={(e) => updateField("category", e.target.value)}
              placeholder={t("categoryPlaceholder")}
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
            {t("cancelButton")}
          </button>
          <button
            type="submit"
            disabled={submitting || !form.parent_product_id.trim()}
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card disabled:opacity-50"
          >
            {submitting ? t("creating") : t("createSubmitButton")}
          </button>
        </div>
      </form>
    </div>
  );
}
