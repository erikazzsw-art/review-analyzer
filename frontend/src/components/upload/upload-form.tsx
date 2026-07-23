"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useMessages, useTranslations } from "next-intl";

import { AsinFetchPanel } from "@/components/upload/asin-fetch-panel";
import { AsinWatchlistPanel } from "@/components/upload/asin-watchlist-panel";
import {
  describeRequestError,
  fetchTaxonomyCategories,
  searchProducts,
  submitUploadJob,
} from "@/lib/api/browser";
import type { DuplicateBatchError } from "@/lib/api/browser";
import { track } from "@/lib/analytics";
import type {
  TaxonomyCategoriesResponse,
  TaxonomyCategoryGroup,
  UploadJob,
  ProductSearchItem,
} from "@/lib/api/types";
import { renderInline } from "@/lib/render-inline";

type UploadMode = "file" | "asin" | "watchlist";

const workflowPurposeKeys = [
  "purposeCompetitor",
  "purposeNewProduct",
  "purposeDaily",
  "purposeListing",
  "purposeQuality",
  "purposeVersion",
] as const;

const PLATFORMS = ["Amazon", "AliExpress", "eBay", "Shopee", "Walmart"] as const;

function normalizeProductLookup(value: string): string {
  return value
    .normalize("NFKC")
    .toLocaleLowerCase()
    .replace(/[\p{P}\p{S}\s_]+/gu, "");
}

function productSimilarity(a: string, b: string): number {
  const left = normalizeProductLookup(a);
  const right = normalizeProductLookup(b);
  if (!left || !right) return 0;
  if (left === right) return 1;
  if (left.includes(right) || right.includes(left)) {
    return 0.92 * Math.min(left.length, right.length) / Math.max(left.length, right.length);
  }
  const rows = left.length + 1;
  const cols = right.length + 1;
  const dp = Array.from({ length: rows }, () => Array<number>(cols).fill(0));
  for (let i = 0; i < rows; i += 1) dp[i][0] = i;
  for (let j = 0; j < cols; j += 1) dp[0][j] = j;
  for (let i = 1; i < rows; i += 1) {
    for (let j = 1; j < cols; j += 1) {
      const cost = left[i - 1] === right[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(
        dp[i - 1][j] + 1,
        dp[i][j - 1] + 1,
        dp[i - 1][j - 1] + cost,
      );
    }
  }
  const distance = dp[left.length][right.length];
  return 1 - distance / Math.max(left.length, right.length);
}

type FormState = {
  productId: string;
  productName: string;
  platform: string;
  parentCategory: string;
  category: string;
  version: string;
  workflowPurpose: string;
  versionNotes: string;
};

function sortedSubCategories(group: TaxonomyCategoryGroup): string[] {
  return [...group.sub_categories].sort((a, b) => {
    const labelA = group.sub_category_labels[a] || a;
    const labelB = group.sub_category_labels[b] || b;
    return labelA.localeCompare(labelB, undefined, { sensitivity: "base" });
  });
}

function CategoryHitBanner({
  categoryValue,
  displayName,
  hit,
  supportedCount,
  supportedCategories,
  t,
}: {
  categoryValue: string;
  displayName: string;
  hit: { categoryKey: string; categoryLabel: string } | null;
  supportedCount: number;
  supportedCategories: TaxonomyCategoriesResponse["supported_categories"];
  t: (key: string) => string;
}): React.ReactNode {
  const label = displayName || categoryValue;
  if (hit && hit.categoryKey !== "other") {
    return (
      <div className="rounded-card border border-[#cbe9d8] bg-[#eef9f3] px-3 py-2 text-xs leading-5 text-[#3d8b74]">
        ✅ <span className="font-semibold">{label}</span> {t("categoryHitSuccess")}
        <span className="mx-1 font-semibold">{hit.categoryLabel}</span>
        {t("categoryHitSuffix")}
      </div>
    );
  }
  const labels = supportedCategories.map((g) => g.category_label).join(" / ");
  return (
    <div className="rounded-card border border-[#f6dbb4] bg-[#fff6e6] px-3 py-2 text-xs leading-5 text-[#9a6118]">
      ⚠️ <span className="font-semibold">{label}</span> {t("categoryHitFallback")}
      {supportedCount} {t("categoryHitFallbackSuffix")}（{t("categoryHitSupported")}：{labels}）
    </div>
  );
}

export function UploadForm() {
  const router = useRouter();
  const t = useTranslations("upload");
  const locale = useLocale();
  const messages = useMessages();
  const [uploadMode, setUploadMode] = useState<UploadMode>("file");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<UploadJob | null>(null);
  const [error, setError] = useState<string>("");
  const [duplicate, setDuplicate] = useState<DuplicateBatchError | null>(null);
  const [similarProducts, setSimilarProducts] = useState<ProductSearchItem[]>([]);
  const [pendingParentName, setPendingParentName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [taxonomy, setTaxonomy] = useState<TaxonomyCategoriesResponse | null>(null);
  const [form, setForm] = useState<FormState>({
    productId: "",
    productName: "",
    platform: "Amazon",
    parentCategory: "",
    category: "",
    version: "V1",
    workflowPurpose: "purposeDaily",
    versionNotes: "",
  });

  useEffect(() => {
    let cancelled = false;
    fetchTaxonomyCategories(locale)
      .then((data) => {
        if (!cancelled) {
          setTaxonomy(data);
          const firstGroup = data.supported_categories[0];
          setForm((prev) => {
            const selectedGroup =
              data.supported_categories.find((group) => group.category_key === prev.parentCategory) ??
              firstGroup;
            if (!selectedGroup) {
              return prev;
            }
            const sorted = sortedSubCategories(selectedGroup);
            const nextCategory = selectedGroup.sub_categories.includes(prev.category)
              ? prev.category
              : sorted[0] ?? "";
            return {
              ...prev,
              parentCategory: selectedGroup.category_key,
              category: nextCategory,
            };
          });
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [locale]);

  const supportedSubCategories = useMemo(() => {
    if (!taxonomy) {
      return new Map<string, { categoryKey: string; categoryLabel: string }>();
    }
    const m = new Map<string, { categoryKey: string; categoryLabel: string }>();
    for (const group of taxonomy.supported_categories) {
      for (const sub of group.sub_categories) {
        m.set(sub, { categoryKey: group.category_key, categoryLabel: group.category_label });
      }
    }
    for (const sub of taxonomy.unknown_sub_categories) {
      m.set(sub, { categoryKey: "other", categoryLabel: t("unknownCategory") });
    }
    return m;
  }, [taxonomy, t]);

  const filteredSubCategories = useMemo(() => {
    if (!taxonomy || !form.parentCategory) return [];
    const group = taxonomy.supported_categories.find(
      (g) => g.category_key === form.parentCategory,
    );
    if (!group) return [];
    return sortedSubCategories(group);
  }, [taxonomy, form.parentCategory]);

  const currentGroupLabels = useMemo(() => {
    if (!taxonomy || !form.parentCategory) {
      return {} as Record<string, string>;
    }
    const group = taxonomy.supported_categories.find(
      (g) => g.category_key === form.parentCategory,
    );
    return group?.sub_category_labels ?? ({} as Record<string, string>);
  }, [taxonomy, form.parentCategory]);

  function subCategoryDisplay(sub: string): string {
    return currentGroupLabels[sub] || sub;
  }

  const categoryHit = useMemo(() => {
    const trimmed = form.category.trim();
    if (!trimmed) return null;
    return supportedSubCategories.get(trimmed) ?? null;
  }, [form.category, supportedSubCategories]);

  const canSubmit = useMemo(() => {
    return (
      !!file &&
      form.productName.trim().length > 0 &&
      form.version.trim().length > 0 &&
      form.workflowPurpose.trim().length > 0
    );
  }, [file, form.productName, form.version, form.workflowPurpose]);

  const jobInProgress = !!job && (job.status === "queued" || job.status === "processing");

  async function findSimilarProducts(parentName: string): Promise<ProductSearchItem[]> {
    try {
      const response = await searchProducts(parentName, 8);
      return response.items
        .filter((item) => {
          const existingName = item.parent_product_id.trim();
          if (!existingName || existingName === parentName) return false;
          return productSimilarity(parentName, existingName) >= 0.82;
        })
        .slice(0, 3);
    } catch {
      return [];
    }
  }

  async function submitWithParentName(parentName: string) {
    setError("");
    setDuplicate(null);
    setSimilarProducts([]);
    setPendingParentName("");
    setIsSubmitting(true);
    track("upload_start", {
      file_type: file?.name.split(".").pop(),
      file_size_kb: file ? Math.round(file.size / 1024) : 0,
      category: form.category,
      workflow_purpose: t(form.workflowPurpose),
    });
    try {
      if (!file) {
        throw new Error(t("validationError"));
      }
      const response = await submitUploadJob({
        sourceFile: file,
        productId: parentName,
        version: form.version.trim(),
        workflowPurpose: t(form.workflowPurpose).trim(),
        productName: parentName,
        platform: form.platform.trim(),
        category: form.category.trim(),
        dateStart: "",
        dateEnd: "",
        versionNotes: form.versionNotes.trim(),
        representativeAsin: form.productId.trim() || null,
      });
      setJob(response.job);
      track("upload_complete", { job_id: response.job.id });
      if (response.job.status === "done" && response.job.session_id) {
        router.push(`/analysis/results?product_id=${encodeURIComponent(parentName)}&session_id=${response.job.session_id}&version=${encodeURIComponent(form.version.trim())}`);
      } else {
        router.push(`/analysis/results?job_id=${response.job.id}&version=${encodeURIComponent(form.version.trim())}`);
      }
    } catch (submitError) {
      const candidate = submitError as { status?: number; message?: string; existingSessionId?: number };
      if (candidate.status === 409 && candidate.existingSessionId) {
        setDuplicate(candidate as DuplicateBatchError);
        track("upload_duplicate", { existing_session_id: candidate.existingSessionId });
      } else {
        const detail = candidate.message || describeRequestError(submitError, "/api/uploads");
        setError(detail);
        track("upload_fail", { error: detail });
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmit() {
    if (!file || !canSubmit) {
      setError(t("validationError"));
      return;
    }

    setError("");
    setDuplicate(null);
    setSimilarProducts([]);
    setIsSubmitting(true);
    const parentName = form.productName.trim();
    const candidates = await findSimilarProducts(parentName);
    if (candidates.length > 0) {
      setPendingParentName(parentName);
      setSimilarProducts(candidates);
      setIsSubmitting(false);
      return;
    }
    await submitWithParentName(parentName);
  }

  return (
    <section className="space-y-6">
      <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
          {t("step1")}
        </div>
        <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          {t("importTitle")}
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-soft">
          {t("importDesc")}
        </p>

        <div className="mt-5 flex gap-1 rounded-pill border border-line bg-[#f8f6f9] p-1">
          <button
            type="button"
            onClick={() => setUploadMode("file")}
            className={`flex-1 rounded-pill px-4 py-2 text-sm font-semibold transition ${uploadMode === "file" ? "bg-white text-ink shadow-sm" : "text-soft hover:text-ink"}`}
          >
            {t("modeFile")}
          </button>
          <button
            type="button"
            onClick={() => setUploadMode("asin")}
            className={`flex-1 rounded-pill px-4 py-2 text-sm font-semibold transition ${uploadMode === "asin" ? "bg-white text-ink shadow-sm" : "text-soft hover:text-ink"}`}
          >
            {t("modeAsin")}
          </button>
          <button
            type="button"
            onClick={() => setUploadMode("watchlist")}
            className={`flex-1 rounded-pill px-4 py-2 text-sm font-semibold transition ${uploadMode === "watchlist" ? "bg-white text-ink shadow-sm" : "text-soft hover:text-ink"}`}
          >
            {t("modeWatchlist")}
          </button>
        </div>

        {uploadMode === "asin" ? (
          <div className="mt-6">
            <AsinFetchPanel />
          </div>
        ) : uploadMode === "watchlist" ? (
          <div className="mt-6">
            <AsinWatchlistPanel />
          </div>
        ) : (
        <>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">{t("productName")}</span>
            <input
              value={form.productName}
              onChange={(event) =>
                setForm((current) => ({ ...current, productName: event.target.value }))
              }
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
              placeholder={t("productNamePlaceholder")}
              required
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">
              {form.platform === "Amazon" ? t("representativeAsinLabel") : form.platform === "AliExpress" ? t("representativeProductIdLabel") : t("representativeProductIdLabel")}
            </span>
            <input
              value={form.productId}
              onChange={(event) =>
                setForm((current) => ({ ...current, productId: event.target.value }))
              }
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
              placeholder={
                form.platform === "Amazon" ? t("representativeAsinPlaceholder") :
                form.platform === "AliExpress" ? t("representativeProductIdPlaceholder") :
                t("representativeProductIdPlaceholder")
              }
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">{t("platform")}</span>
            <select
              value={form.platform}
              onChange={(event) =>
                setForm((current) => ({ ...current, platform: event.target.value }))
              }
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            >
              {PLATFORMS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">
              {t("parentCategory")}
            </span>
            <select
              value={form.parentCategory}
              onChange={(event) => {
                const key = event.target.value;
                const group = taxonomy?.supported_categories.find(
                  (g) => g.category_key === key,
                );
                const sorted = group ? sortedSubCategories(group) : [];
                setForm((current) => ({
                  ...current,
                  parentCategory: key,
                  category: sorted[0] ?? "",
                }));
              }}
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            >
              {!taxonomy && (
                <option value="">{t("categoryLoading")}</option>
              )}
              {taxonomy?.supported_categories.map((g) => (
                <option key={g.category_key} value={g.category_key}>
                  {g.category_label}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">
              {t("subCategory")}
            </span>
            <select
              value={form.category}
              onChange={(event) =>
                setForm((current) => ({ ...current, category: event.target.value }))
              }
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            >
              {filteredSubCategories.map((sub) => (
                <option key={sub} value={sub}>
                  {subCategoryDisplay(sub)}
                </option>
              ))}
            </select>
            {taxonomy && form.category.trim().length > 0 && (
              <CategoryHitBanner
                categoryValue={form.category.trim()}
                displayName={subCategoryDisplay(form.category.trim())}
                hit={categoryHit}
                supportedCount={taxonomy.total_sub_categories}
                supportedCategories={taxonomy.supported_categories}
                t={t}
              />
            )}
          </label>
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">{t("version")}</span>
            <input
              value={form.version}
              onChange={(event) =>
                setForm((current) => ({ ...current, version: event.target.value }))
              }
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">{t("workflowPurpose")}</span>
            <select
              value={form.workflowPurpose}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  workflowPurpose: event.target.value,
                }))
              }
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            >
              {workflowPurposeKeys.map((key) => (
                <option key={key} value={key}>
                  {t(key)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="mt-4 block space-y-2">
          <span className="text-sm font-semibold text-ink">{t("versionNotes")}</span>
          <textarea
            value={form.versionNotes}
            onChange={(event) =>
              setForm((current) => ({ ...current, versionNotes: event.target.value }))
            }
            className="min-h-28 w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            placeholder={t("versionNotesPlaceholder")}
          />
        </label>

        <div className="mt-4 rounded-card border border-dashed border-line bg-[#fffafb] px-5 py-5">
          <label className="block cursor-pointer">
            <input
              type="file"
              accept=".csv,.xlsx,.xls,.docx,.txt"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="hidden"
            />
            <div className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-ink">{t("selectFile")}</span>
              <span className="text-sm leading-7 text-soft">
                {t("fileHint")}
              </span>
              <span className="inline-flex w-fit rounded-pill bg-white px-4 py-2 text-xs font-semibold text-soft">
                {file ? file.name : t("noFile")}
              </span>
            </div>
          </label>
        </div>

        {duplicate ? (
          <div className="mt-4 rounded-card border border-[#f6dbb4] bg-[#fff6e6] px-4 py-4 text-sm leading-7 text-[#9a6118]">
            <p className="font-semibold">{t("duplicateWarning")}</p>
            <p className="mt-1 text-xs text-[#9a6118]/80">
              {t("duplicateDetail", {
                title: duplicate.existingTitle,
                totalReviews: String(duplicate.totalReviews),
                createdAt: duplicate.existingCreatedAt,
              })}
            </p>
            <button
              type="button"
              onClick={() => router.push(`/analysis/results?session_id=${duplicate.existingSessionId}`)}
              className="mt-3 inline-flex items-center rounded-pill bg-[#9a6118] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#7a4d13]"
            >
              {t("viewExistingResult")}
            </button>
          </div>
        ) : null}

        {similarProducts.length > 0 ? (
          <div className="mt-4 rounded-card border border-[#f6dbb4] bg-[#fff6e6] px-4 py-4 text-sm leading-7 text-[#9a6118]">
            <p className="font-semibold">{t("similarProductTitle")}</p>
            <p className="mt-1 text-xs text-[#9a6118]/80">
              {t("similarProductDesc", { name: pendingParentName })}
            </p>
            <div className="mt-3 space-y-2">
              {similarProducts.map((item) => (
                <div
                  key={item.parent_product_id}
                  className="flex flex-col gap-2 rounded-card border border-[#f1d29c] bg-white/70 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <div className="text-sm font-semibold text-ink">{item.parent_product_id}</div>
                    <div className="mt-0.5 text-xs text-soft">
                      {item.review_count} {t("similarProductReviews")} · {item.variants.length} {t("similarProductVariants")}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => submitWithParentName(item.parent_product_id)}
                    className="inline-flex min-h-9 items-center justify-center rounded-pill bg-[#9a6118] px-4 py-2 text-xs font-semibold text-white transition hover:bg-[#7a4d13]"
                  >
                    {t("useExistingProduct")}
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => submitWithParentName(pendingParentName || form.productName.trim())}
              className="mt-3 inline-flex min-h-9 items-center justify-center rounded-pill border border-[#e3bc7b] bg-white px-4 py-2 text-xs font-semibold text-[#9a6118] transition hover:bg-[#fff9ef]"
            >
              {t("createNewProductAnyway")}
            </button>
          </div>
        ) : null}

        {error ? (
          <div className="mt-4 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]">
            {error}
          </div>
        ) : null}

        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || !canSubmit || jobInProgress}
            className="inline-flex min-h-12 items-center justify-center rounded-pill bg-ink px-6 py-3 text-sm font-semibold text-white shadow-card transition disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? t("submitting") : jobInProgress ? t("submittedAnalyzing") : t("submitButton")}
          </button>
          <button
            type="button"
            onClick={() => router.push("/workspace")}
            className="inline-flex min-h-12 items-center justify-center rounded-pill border border-line bg-white px-6 py-3 text-sm font-semibold text-ink transition hover:bg-[#fffafb]"
          >
            {t("backToWorkspace")}
          </button>
        </div>
        </>
        )}
        <p className="mt-4 text-xs leading-5 text-soft/70">
          {renderInline((messages as Record<string, Record<string, string>>)?.upload?.uploadNotice ?? "")}
        </p>
      </div>
    </section>
  );
}
