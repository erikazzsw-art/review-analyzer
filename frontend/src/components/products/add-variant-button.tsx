"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";

import { addProductVariant, type ProductVariantCreatePayload } from "@/lib/api/browser";

type AddVariantButtonProps = {
  productId: number;
  defaultPlatform?: string | null;
};

type VariantForm = {
  child_asin: string;
  variant_sku: string;
  name: string;
  platform: string;
  color: string;
  size: string;
  style: string;
  material: string;
  brand: string;
  price: string;
  price_currency: string;
  fulfillment: "" | "fba" | "fbm";
  listing_date: string;
  launched_at: string;
};

const emptyForm = (platform?: string | null): VariantForm => ({
  child_asin: "",
  variant_sku: "",
  name: "",
  platform: platform || "Amazon",
  color: "",
  size: "",
  style: "",
  material: "",
  brand: "",
  price: "",
  price_currency: "USD",
  fulfillment: "",
  listing_date: "",
  launched_at: "",
});

function cleanText(value: string): string | undefined {
  const text = value.trim();
  return text || undefined;
}

function cleanNumber(value: string): number | undefined {
  const text = value.trim().replace(/,/g, "");
  if (!text) return undefined;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error) return err.message;
  if (err && typeof err === "object" && "message" in err) {
    const message = String((err as { message?: unknown }).message || "").trim();
    if (message) return message;
  }
  return fallback;
}

export function AddVariantButton({ productId, defaultPlatform }: AddVariantButtonProps) {
  const t = useTranslations("products.addVariant");
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<VariantForm>(() => emptyForm(defaultPlatform));

  function updateField<K extends keyof VariantForm>(key: K, value: VariantForm[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function closeDialog() {
    if (submitting) return;
    setOpen(false);
    setError("");
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const childAsin = form.child_asin.trim().toUpperCase();
    if (!childAsin) return;

    const payload: ProductVariantCreatePayload = {
      child_asin: childAsin,
      variant_sku: cleanText(form.variant_sku) || childAsin,
      name: cleanText(form.name),
      platform: cleanText(form.platform) || defaultPlatform || undefined,
      color: cleanText(form.color),
      size: cleanText(form.size),
      style: cleanText(form.style),
      material: cleanText(form.material),
      brand: cleanText(form.brand),
      price: cleanNumber(form.price),
      price_currency: cleanText(form.price_currency),
      is_fba:
        form.fulfillment === "fba"
          ? true
          : form.fulfillment === "fbm"
            ? false
            : undefined,
      listing_date: cleanText(form.listing_date),
      launched_at: cleanText(form.launched_at),
      status: "active",
    };

    setSubmitting(true);
    setError("");
    try {
      await addProductVariant(productId, payload);
      setOpen(false);
      setForm(emptyForm(defaultPlatform));
      router.refresh();
    } catch (err) {
      setError(errorMessage(err, t("saveFailed")));
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex h-9 items-center justify-center gap-2 rounded-pill border border-line bg-white px-3 text-sm font-semibold text-ink shadow-sm transition hover:border-[#4a7dc7]/40 hover:bg-[#f7fbff]"
      >
        <Plus className="h-4 w-4" />
        {t("button")}
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <form
        onSubmit={handleSubmit}
        className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-shell border border-line bg-white p-6 shadow-card"
      >
        <div>
          <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            {t("title")}
          </h3>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("asinLabel")}
            </span>
            <input
              type="text"
              value={form.child_asin}
              onChange={(event) => updateField("child_asin", event.target.value)}
              placeholder={t("asinPlaceholder")}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
              required
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("platformLabel")}
            </span>
            <input
              type="text"
              value={form.platform}
              onChange={(event) => updateField("platform", event.target.value)}
              placeholder="Amazon"
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("variantSkuLabel")}
            </span>
            <input
              type="text"
              value={form.variant_sku}
              onChange={(event) => updateField("variant_sku", event.target.value)}
              placeholder={t("variantSkuPlaceholder")}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("variantNameLabel")}
            </span>
            <input
              type="text"
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
              placeholder={t("variantNamePlaceholder")}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("colorLabel")}
            </span>
            <input
              type="text"
              value={form.color}
              onChange={(event) => updateField("color", event.target.value)}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("sizeLabel")}
            </span>
            <input
              type="text"
              value={form.size}
              onChange={(event) => updateField("size", event.target.value)}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("styleLabel")}
            </span>
            <input
              type="text"
              value={form.style}
              onChange={(event) => updateField("style", event.target.value)}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("materialLabel")}
            </span>
            <input
              type="text"
              value={form.material}
              onChange={(event) => updateField("material", event.target.value)}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("brandLabel")}
            </span>
            <input
              type="text"
              value={form.brand}
              onChange={(event) => updateField("brand", event.target.value)}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                {t("priceLabel")}
              </span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.price}
                onChange={(event) => updateField("price", event.target.value)}
                className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
              />
            </label>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                {t("currencyLabel")}
              </span>
              <input
                type="text"
                value={form.price_currency}
                onChange={(event) => updateField("price_currency", event.target.value)}
                className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
              />
            </label>
          </div>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("fulfillmentLabel")}
            </span>
            <select
              value={form.fulfillment}
              onChange={(event) => updateField("fulfillment", event.target.value as VariantForm["fulfillment"])}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            >
              <option value="">{t("fulfillmentUnknown")}</option>
              <option value="fba">FBA</option>
              <option value="fbm">FBM</option>
            </select>
          </label>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("listingDateLabel")}
            </span>
            <input
              type="date"
              value={form.listing_date}
              onChange={(event) => updateField("listing_date", event.target.value)}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              {t("launchedAtLabel")}
            </span>
            <input
              type="date"
              value={form.launched_at}
              onChange={(event) => updateField("launched_at", event.target.value)}
              className="mt-1 w-full rounded-card border border-line bg-white px-4 py-3 text-sm text-ink outline-none focus:border-[#4a7dc7]"
            />
          </label>
        </div>

        {error && (
          <p className="mt-4 rounded-card bg-[#fff2f3] px-4 py-3 text-sm font-semibold text-[#b44655]">
            {error}
          </p>
        )}

        <div className="mt-8 flex justify-end gap-3">
          <button
            type="button"
            onClick={closeDialog}
            disabled={submitting}
            className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-soft"
          >
            {t("cancelButton")}
          </button>
          <button
            type="submit"
            disabled={submitting || !form.child_asin.trim()}
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card disabled:opacity-50"
          >
            {submitting ? t("saving") : t("submitButton")}
          </button>
        </div>
      </form>
    </div>
  );
}
