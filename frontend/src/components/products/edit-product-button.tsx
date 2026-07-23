"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Pencil } from "lucide-react";
import { useTranslations } from "next-intl";
import { createPortal } from "react-dom";

import { updateProduct, type ProductUpdatePayload } from "@/lib/api/browser";

const lifecycleKeys = [
  { value: "research", key: "lifecycleResearch" },
  { value: "launch", key: "lifecycleLaunch" },
  { value: "growth", key: "lifecycleGrowth" },
  { value: "mature", key: "lifecycleMature" },
  { value: "decline", key: "lifecycleDecline" },
] as const;

const platformOptions = ["Amazon", "eBay", "Shopee", "AliExpress", "Walmart"];
const AMAZON_ASIN_PATTERN = /^B[A-Z0-9]{9}$/i;

function isAmazonAsin(value: string | undefined): boolean {
  return AMAZON_ASIN_PATTERN.test((value || "").trim());
}

type EditProductButtonProps = {
  productId: number;
  initial: {
    parent_product_id?: string;
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
  const t = useTranslations("products");
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<ProductUpdatePayload>({
    parent_product_id: initial.parent_product_id ?? "",
    name: initial.name ?? initial.parent_product_id ?? "",
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
    const productName = form.name?.trim() || "";
    if (!productName) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload: ProductUpdatePayload = {};
      payload.name = productName;
      if (!isAmazonAsin(initial.parent_product_id)) {
        payload.parent_product_id = productName;
      }
      if (form.platform) payload.platform = form.platform;
      if (form.category?.trim()) payload.category = form.category.trim();
      if (form.lifecycle_stage) payload.lifecycle_stage = form.lifecycle_stage;
      if (form.current_version?.trim()) payload.current_version = form.current_version.trim();
      if (form.core_selling_points?.trim()) payload.core_selling_points = form.core_selling_points.trim();
      if (form.main_competitors?.trim()) payload.main_competitors = form.main_competitors.trim();
      await updateProduct(productId, payload);
      setOpen(false);
      router.refresh();
    } catch (err) {
      const message = err && typeof err === "object" && "message" in err
        ? String((err as { message?: unknown }).message)
        : t("edit.saveFailed");
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  const trigger = (
    <button
      type="button"
      onClick={() => {
        setError(null);
        setOpen(true);
      }}
      className="inline-flex min-h-9 items-center justify-center gap-1.5 rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-ink transition hover:border-ink/30"
    >
      <Pencil className="h-3.5 w-3.5" />
      {t("edit.editButton")}
    </button>
  );

  if (!open || typeof document === "undefined") {
    return trigger;
  }

  return (
    <>
      {trigger}
      {createPortal(
        <div className="fixed inset-0 z-[100] overflow-y-auto bg-black/40 px-4 py-3 sm:py-6">
          <form
            onSubmit={handleSubmit}
            className="mx-auto w-full max-w-lg rounded-shell border border-line bg-white p-6 shadow-card"
          >
            <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              {t("edit.editTitle")}
            </h3>

            <div className="mt-6">
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                    {t("edit.productNameLabel")}
                  </label>
                  <input
                    type="text"
                    value={form.name ?? ""}
                    onChange={(e) => updateField("name", e.target.value)}
                    placeholder={t("edit.productNamePlaceholder")}
                    className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
                    required
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                      {t("edit.platformLabel")}
                    </label>
                    <select
                      value={form.platform ?? "Amazon"}
                      onChange={(e) => updateField("platform", e.target.value)}
                      className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
                    >
                      {platformOptions.map((p) => (
                        <option key={p} value={p}>{p}</option>
                      ))}
                      <option value="其他">{t("create.platformOther")}</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                      {t("edit.lifecycleLabel")}
                    </label>
                    <select
                      value={form.lifecycle_stage ?? "growth"}
                      onChange={(e) => updateField("lifecycle_stage", e.target.value)}
                      className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
                    >
                      {lifecycleKeys.map((opt) => (
                        <option key={opt.value} value={opt.value}>{t(`create.${opt.key}`)}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                    {t("edit.categoryLabel")}
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
                    {t("edit.coreSellingPointsLabel")}
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
                    {t("edit.mainCompetitorsLabel")}
                  </label>
                  <textarea
                    value={form.main_competitors ?? ""}
                    onChange={(e) => updateField("main_competitors", e.target.value)}
                    rows={2}
                    className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
                  />
                </div>
              </div>

              {error && (
                <p className="mt-4 rounded-card border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {error}
                </p>
              )}
            </div>

            <div className="mt-8 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setOpen(false);
                }}
                disabled={submitting}
                className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-soft"
              >
                {t("edit.cancelButton")}
              </button>
              <button
                type="submit"
                disabled={submitting || !form.name?.trim()}
                className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card disabled:opacity-50"
              >
                {submitting ? t("edit.saving") : t("edit.saveButton")}
              </button>
            </div>
          </form>
        </div>,
        document.body,
      )}
    </>
  );
}
