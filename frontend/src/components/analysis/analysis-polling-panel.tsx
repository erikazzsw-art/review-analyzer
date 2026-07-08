"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, CheckCircle2, PackageSearch } from "lucide-react";
import { useTranslations } from "next-intl";

import { fetchUploadJob } from "@/lib/api/browser";
import type { UploadJob } from "@/lib/api/types";

type StepStatus = "completed" | "active" | "pending" | "error";

function getStepStatuses(job: UploadJob | null): StepStatus[] {
  if (!job) return ["active", "pending", "pending", "pending"];

  const { status, total_rows } = job;

  if (status === "failed") {
    if (total_rows === 0) return ["completed", "error", "pending", "pending"];
    return ["completed", "completed", "error", "pending"];
  }
  if (status === "queued" && total_rows === 0)
    return ["active", "pending", "pending", "pending"];
  if (status === "fetching")
    return ["completed", "active", "pending", "pending"];
  if ((status === "queued" && total_rows > 0) || status === "processing")
    return ["completed", "completed", "active", "pending"];
  if (status === "done")
    return ["completed", "completed", "completed", "completed"];

  return ["active", "pending", "pending", "pending"];
}

function StepperStrip({ statuses, labels }: { statuses: StepStatus[]; labels: string[] }) {
  return (
    <div className="flex w-full max-w-md items-center">
      {statuses.map((s, i) => (
        <div key={i} className="flex flex-1 items-center last:flex-none">
          {/* Step circle */}
          <div className="flex flex-col items-center gap-1.5">
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition-all ${
                s === "completed"
                  ? "bg-[#7c3aed] text-white"
                  : s === "active"
                    ? "border-2 border-[#7c3aed] bg-white text-[#7c3aed]"
                    : s === "error"
                      ? "bg-[#fef2f2] text-[#dc2626]"
                      : "border-2 border-gray-200 bg-white text-gray-400"
              }`}
            >
              {s === "completed" && <CheckCircle2 className="h-4 w-4" />}
              {s === "active" && (
                <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#7c3aed]" />
              )}
              {s === "error" && <AlertCircle className="h-4 w-4" />}
              {s === "pending" && <span className="h-2 w-2 rounded-full bg-gray-300" />}
            </div>
            <span
              className={`text-[11px] whitespace-nowrap ${
                s === "active" || s === "completed"
                  ? "font-medium text-ink"
                  : s === "error"
                    ? "font-medium text-[#dc2626]"
                    : "text-soft"
              }`}
            >
              {labels[i]}
            </span>
          </div>
          {/* Connector line */}
          {i < statuses.length - 1 && (
            <div
              className={`mx-1.5 h-0.5 flex-1 rounded-full transition-all ${
                statuses[i + 1] === "completed" || statuses[i + 1] === "active"
                  ? "bg-[#7c3aed]"
                  : statuses[i + 1] === "error"
                    ? "bg-[#fca5a5]"
                    : "bg-gray-200"
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

export function AnalysisPollingPanel({ jobId }: { jobId: number }) {
  const router = useRouter();
  const t = useTranslations("analysis.polling");
  const [job, setJob] = useState<UploadJob | null>(null);
  const [error, setError] = useState("");
  const [isStale, setIsStale] = useState(false);
  const lastStatusRef = useRef<{ status: string; at: number }>({ status: "", at: Date.now() });

  const steps = [t("step1"), t("step2"), t("step3"), t("step4")];

  function statusMessage(job: UploadJob | null): string {
    if (!job) return t("statusConnecting");
    if (job.status === "queued" && job.total_rows === 0) return t("statusQueued");
    if (job.status === "fetching")
      return job.error_message || t("statusFetching");
    if (job.status === "processing" || (job.status === "queued" && job.total_rows > 0))
      return t("statusProcessing");
    if (job.status === "done") return t("statusDone");
    return t("statusFailed");
  }

  function friendlyError(msg: string | null): string {
    if (!msg) return t("unknownError");
    if (msg.toLowerCase().includes("timeout")) return t("timeoutError");
    if (msg.toLowerCase().includes("rate limit")) return t("rateLimitError");
    if (msg.toLowerCase().includes("quota")) return msg;
    return msg;
  }

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const response = await fetchUploadJob(jobId);
        if (cancelled) return;
        setJob(response.job);
        setError("");

        // Stale detection
        if (response.job.status !== lastStatusRef.current.status) {
          lastStatusRef.current = { status: response.job.status, at: Date.now() };
          setIsStale(false);
        } else if (Date.now() - lastStatusRef.current.at > 60_000) {
          setIsStale(true);
        }

        // Terminal: done with session → redirect
        if (response.job.status === "done" && response.job.session_id) {
          router.replace(`/analysis/results?session_id=${response.job.session_id}`);
          return;
        }
        // Terminal: done without session (0 reviews)
        if (response.job.status === "done" && !response.job.session_id) {
          return;
        }
        // Terminal: failed
        if (response.job.status === "failed") {
          return;
        }

        timer = window.setTimeout(poll, 2000);
      } catch (err) {
        if (cancelled) return;
        setError((err as { message?: string }).message || t("pollingFailure"));
        // Retry after error
        timer = window.setTimeout(poll, 5000);
      }
    }

    let timer: number | null = null;
    poll();

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [jobId, router, t]);

  const stepStatuses = getStepStatuses(job);
  const progress =
    job && job.total_rows > 0
      ? Math.round((job.processed_rows / job.total_rows) * 100)
      : 0;

  const isInProgress =
    !job ||
    job.status === "queued" ||
    job.status === "fetching" ||
    job.status === "processing";

  const isDoneNoSession = job?.status === "done" && !job.session_id;
  const isFailed = job?.status === "failed";

  return (
    <section className="rounded-shell border border-line bg-white/84 p-8 shadow-card backdrop-blur">
      <div className="flex flex-col items-center gap-6 text-center">
        {/* Stepper */}
        {job && <StepperStrip statuses={stepStatuses} labels={steps} />}

        {/* In-progress states */}
        {isInProgress && !error && (
          <>
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-[#f3f0f5] border-t-[#7c3aed]" />
            <div>
              <h2 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                {statusMessage(job)}
              </h2>
              <p className="mt-2 text-sm text-soft">
                {t("description")}
              </p>
            </div>
            {job && job.total_rows > 0 && (
              <div className="w-full max-w-sm">
                <div className="flex items-center justify-between text-xs text-soft">
                  <span>{t("processedFormat", { processed: job.processed_rows, total: job.total_rows })}</span>
                  <span>{progress}%</span>
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-[#f3f0f5]">
                  <div
                    className="h-full rounded-full bg-[#7c3aed] transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                {job.positive_count + job.negative_count > 0 && (
                  <div className="mt-2 text-xs text-soft">
                    {t("sentimentSplit", { positive: job.positive_count, negative: job.negative_count })}
                  </div>
                )}
              </div>
            )}
            {isStale && (
              <div className="rounded-card border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-700">
                {t("staleWarning")}
              </div>
            )}
          </>
        )}

        {/* Done but no reviews found */}
        {isDoneNoSession && (
          <>
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#f5f3ff]">
              <PackageSearch className="h-7 w-7 text-[#7c3aed]" />
            </div>
            <div>
              <h2 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                {t("noReviewsTitle")}
              </h2>
              <p className="mt-2 text-sm text-soft">
                {job.error_message || t("noReviewsDefaultMsg")}
              </p>
              <p className="mt-3 text-xs text-soft/80">
                {t("noReviewsReasons")}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => router.push("/upload")}
                className="inline-flex min-h-10 items-center justify-center rounded-pill bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-card"
              >
                {t("retry")}
              </button>
              <button
                type="button"
                onClick={() => router.push("/upload")}
                className="inline-flex min-h-10 items-center justify-center rounded-pill border border-line bg-white px-5 py-2.5 text-sm font-semibold text-ink"
              >
                {t("changeProduct")}
              </button>
            </div>
          </>
        )}

        {/* Failed state */}
        {isFailed && (
          <>
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#fef2f2]">
              <AlertCircle className="h-7 w-7 text-[#dc2626]" />
            </div>
            <div>
              <h2 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                {t("statusFailed")}
              </h2>
              <p className="mt-2 text-sm text-[#b44655]">
                {friendlyError(job?.error_message ?? null)}
              </p>
            </div>
            <button
              type="button"
              onClick={() => router.push("/upload")}
              className="inline-flex min-h-10 items-center justify-center rounded-pill bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-card"
            >
              {t("retryUpload")}
            </button>
          </>
        )}

        {/* Network error during polling */}
        {error && isInProgress && (
          <div className="rounded-card border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            {t("connectionLost", { error })}
          </div>
        )}
      </div>
    </section>
  );
}

