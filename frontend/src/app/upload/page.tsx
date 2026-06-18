"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { AppShell } from "@/components/app/app-shell";
import { AsinFetchPanel } from "@/components/upload/asin-fetch-panel";
import { AsinWatchlistPanel } from "@/components/upload/asin-watchlist-panel";
import {
  describeRequestError,
  fetchTaxonomyCategories,
  fetchUploadJob,
  submitUploadJob,
} from "@/lib/api/browser";
import { track } from "@/lib/analytics";
import type { TaxonomyCategoriesResponse, UploadJob } from "@/lib/api/types";

type UploadMode = "file" | "asin" | "watchlist";

const workflowPurposeKeys = [
  "purposeCompetitor",
  "purposeNewProduct",
  "purposeDaily",
  "purposeListing",
  "purposeQuality",
  "purposeVersion",
] as const;

type FormState = {
  productId: string;
  productName: string;
  platform: string;
  category: string;
  version: string;
  workflowPurpose: string;
  dateStart: string;
  dateEnd: string;
  versionNotes: string;
};

function statusTone(status: UploadJob["status"]): string {
  if (status === "done") {
    return "bg-[#e8f8f0] text-[#3d8b74]";
  }
  if (status === "failed") {
    return "bg-[#fdeaea] text-[#c45863]";
  }
  if (status === "processing") {
    return "bg-[#eef6ff] text-[#4a7dc7]";
  }
  return "bg-[#fff1f5] text-[#d94d72]";
}

function CategoryHitBanner({
  categoryValue,
  hit,
  supportedCount,
  supportedCategories,
  t,
}: {
  categoryValue: string;
  hit: { categoryKey: string; categoryLabel: string } | null;
  supportedCount: number;
  supportedCategories: TaxonomyCategoriesResponse["supported_categories"];
  t: (key: string) => string;
}): React.ReactNode {
  if (hit && hit.categoryKey !== "other") {
    return (
      <div className="rounded-card border border-[#cbe9d8] bg-[#eef9f3] px-3 py-2 text-xs leading-5 text-[#3d8b74]">
        ✅ <span className="font-semibold">{categoryValue}</span> {t("categoryHitSuccess")}
        <span className="mx-1 font-semibold">{hit.categoryLabel}</span>
        {t("categoryHitSuffix")}
      </div>
    );
  }
  const labels = supportedCategories.map((g) => g.category_label).join(" / ");
  return (
    <div className="rounded-card border border-[#f6dbb4] bg-[#fff6e6] px-3 py-2 text-xs leading-5 text-[#9a6118]">
      ⚠️ <span className="font-semibold">{categoryValue}</span> {t("categoryHitFallback")}
      {supportedCount} {t("categoryHitFallbackSuffix")}（{t("categoryHitSupported")}：{labels}）
    </div>
  );
}

export default function UploadPage() {
  const router = useRouter();
  const t = useTranslations("upload");
  const [uploadMode, setUploadMode] = useState<UploadMode>("file");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<UploadJob | null>(null);
  const [error, setError] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [taxonomy, setTaxonomy] = useState<TaxonomyCategoriesResponse | null>(null);
  const [form, setForm] = useState<FormState>({
    productId: "",
    productName: "",
    platform: "Amazon",
    category: "家具家居",
    version: "V1",
    workflowPurpose: "purposeDaily",
    dateStart: "",
    dateEnd: "",
    versionNotes: "",
  });

  useEffect(() => {
    let cancelled = false;
    fetchTaxonomyCategories()
      .then((data) => {
        if (!cancelled) {
          setTaxonomy(data);
        }
      })
      .catch(() => {
        // taxonomy 拉取失败不阻断上传流程，前端仅退回到无提示状态
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
      m.set(sub, { categoryKey: "other", categoryLabel: "未归类" });
    }
    return m;
  }, [taxonomy]);

  const categoryHit = useMemo(() => {
    const trimmed = form.category.trim();
    if (!trimmed) return null;
    return supportedSubCategories.get(trimmed) ?? null;
  }, [form.category, supportedSubCategories]);

  const canSubmit = useMemo(() => {
    return (
      !!file &&
      form.productId.trim().length > 0 &&
      form.version.trim().length > 0 &&
      form.workflowPurpose.trim().length > 0
    );
  }, [file, form.productId, form.version, form.workflowPurpose]);

  useEffect(() => {
    if (!job || job.status === "done" || job.status === "failed") {
      return;
    }

    setIsPolling(true);
    const timer = window.setInterval(async () => {
      try {
        const response = await fetchUploadJob(job.id);
        setJob(response.job);
        if (response.job.status === "done") {
          window.clearInterval(timer);
          setIsPolling(false);
          router.push(`/analysis/results?session_id=${response.job.session_id ?? ""}`);
        }
        if (response.job.status === "failed") {
          window.clearInterval(timer);
          setIsPolling(false);
        }
      } catch (pollError) {
        const candidate = pollError as { message?: string };
        setError(candidate.message || t("pollError"));
        window.clearInterval(timer);
        setIsPolling(false);
      }
    }, 1800);

    return () => {
      window.clearInterval(timer);
      setIsPolling(false);
    };
  }, [job, router]);

  async function handleSubmit() {
    if (!file || !canSubmit) {
      setError(t("validationError"));
      return;
    }

    setError("");
    setIsSubmitting(true);
    track("upload_start", {
      file_type: file.name.split(".").pop(),
      file_size_kb: Math.round(file.size / 1024),
      category: form.category,
      workflow_purpose: t(form.workflowPurpose),
    });
    try {
      const response = await submitUploadJob({
        sourceFile: file,
        productId: form.productId.trim(),
        version: form.version.trim(),
        workflowPurpose: t(form.workflowPurpose).trim(),
        productName: form.productName.trim(),
        platform: form.platform.trim(),
        category: form.category.trim(),
        dateStart: form.dateStart.trim(),
        dateEnd: form.dateEnd.trim(),
        versionNotes: form.versionNotes.trim(),
      });
      setJob(response.job);
      track("upload_complete", { job_id: response.job.id });
      if (response.job.status === "done" && response.job.session_id) {
        router.push(`/analysis/results?session_id=${response.job.session_id}`);
      }
    } catch (submitError) {
      const candidate = submitError as { message?: string };
      const detail = candidate.message || describeRequestError(submitError, "/api/uploads");
      setError(detail);
      track("upload_fail", { error: detail });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppShell
      currentPath="/upload"
      title={t("title")}
      description={t("description")}
    >
      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
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
              <span className="text-sm font-semibold text-ink">{t("productId")}</span>
              <input
                value={form.productId}
                onChange={(event) =>
                  setForm((current) => ({ ...current, productId: event.target.value }))
                }
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
                placeholder={t("productIdPlaceholder")}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">{t("productName")}</span>
              <input
                value={form.productName}
                onChange={(event) =>
                  setForm((current) => ({ ...current, productName: event.target.value }))
                }
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
                placeholder={t("productNamePlaceholder")}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">{t("platform")}</span>
              <input
                value={form.platform}
                onChange={(event) =>
                  setForm((current) => ({ ...current, platform: event.target.value }))
                }
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">
                {t("category")}
              </span>
              <input
                value={form.category}
                onChange={(event) =>
                  setForm((current) => ({ ...current, category: event.target.value }))
                }
                list="taxonomy-sub-categories"
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
                placeholder={t("categoryPlaceholder")}
              />
              {taxonomy && (
                <datalist id="taxonomy-sub-categories">
                  {Array.from(supportedSubCategories.keys()).map((sub) => (
                    <option key={sub} value={sub} />
                  ))}
                </datalist>
              )}
              {taxonomy && form.category.trim().length > 0 && (
                <CategoryHitBanner
                  categoryValue={form.category.trim()}
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
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">{t("dateStart")}</span>
              <input
                type="date"
                value={form.dateStart}
                onChange={(event) =>
                  setForm((current) => ({ ...current, dateStart: event.target.value }))
                }
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">{t("dateEnd")}</span>
              <input
                type="date"
                value={form.dateEnd}
                onChange={(event) =>
                  setForm((current) => ({ ...current, dateEnd: event.target.value }))
                }
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
              />
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

          {error ? (
            <div className="mt-4 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]">
              {error}
            </div>
          ) : null}

          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting || !canSubmit}
              className="inline-flex min-h-12 items-center justify-center rounded-pill bg-ink px-6 py-3 text-sm font-semibold text-white shadow-card transition disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? t("submitting") : t("submitButton")}
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
        </div>

        <div className="space-y-6">
          <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
            <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
              {t("step2")}
            </div>
            <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              {t("statusTitle")}
            </h3>
            <div className="mt-4 space-y-4">
              {job ? (
                <>
                  <div className="flex items-center justify-between rounded-card border border-line bg-white px-4 py-4">
                    <span className="text-sm font-semibold text-ink">{t("statusCurrent")}</span>
                    <span className={`rounded-pill px-3 py-1 text-xs font-bold ${statusTone(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-card border border-line bg-[#fffafb] px-4 py-4">
                      <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                        {t("statusProcessed")}
                      </div>
                      <div className="mt-2 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
                        {job.processed_rows}/{job.total_rows}
                      </div>
                    </div>
                    <div className="rounded-card border border-line bg-[#fbf9ff] px-4 py-4">
                      <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                        {t("statusSummary")}
                      </div>
                      <div className="mt-2 text-sm leading-7 text-soft">
                        {t("statusPositive")} {job.positive_count} · {t("statusNegative")} {job.negative_count}
                      </div>
                    </div>
                  </div>
                  {job.error_message ? (
                    <div className="rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-4 text-sm leading-7 text-[#b44655]">
                      {job.error_message}
                    </div>
                  ) : null}
                  <div className="rounded-card border border-line bg-white px-4 py-4 text-sm leading-7 text-soft">
                    {isPolling
                      ? t("statusPolling")
                      : job.status === "done"
                        ? t("statusDone")
                        : job.status === "failed"
                          ? t("statusFailed")
                          : t("statusCreated")}
                  </div>
                </>
              ) : (
                <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-6 text-sm leading-7 text-soft">
                  {t("statusEmpty")}
                </div>
              )}
            </div>
          </section>

          <section className="rounded-shell border border-line bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(252,246,251,0.94))] p-6 shadow-card backdrop-blur">
            <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              {t("whatHappensTitle")}
            </h3>
            <div className="mt-4 space-y-3 text-sm leading-7 text-soft">
              <div className="rounded-card border border-line bg-white px-4 py-4">
                {t("whatHappens1")}
              </div>
              <div className="rounded-card border border-line bg-white px-4 py-4">
                {t("whatHappens2")}
              </div>
              <div className="rounded-card border border-line bg-white px-4 py-4">
                {t("whatHappens3")}
              </div>
            </div>
          </section>
        </div>
      </section>
    </AppShell>
  );
}
