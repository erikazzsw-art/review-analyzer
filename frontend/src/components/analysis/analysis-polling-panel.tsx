"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchUploadJob } from "@/lib/api/browser";
import type { UploadJob } from "@/lib/api/types";

function statusLabel(status: UploadJob["status"]): string {
  if (status === "queued") return "排队中...";
  if (status === "processing") return "分析中...";
  if (status === "done") return "分析完成";
  return "分析失败";
}

export function AnalysisPollingPanel({ jobId }: { jobId: number }) {
  const router = useRouter();
  const [job, setJob] = useState<UploadJob | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const response = await fetchUploadJob(jobId);
        if (cancelled) return;
        setJob(response.job);

        if (response.job.status === "done" && response.job.session_id) {
          router.replace(`/analysis/results?session_id=${response.job.session_id}`);
          return;
        }
        if (response.job.status === "failed") {
          return;
        }

        timer = window.setTimeout(poll, 2000);
      } catch (err) {
        if (cancelled) return;
        setError((err as { message?: string }).message || "轮询失败");
      }
    }

    let timer: number | null = null;
    poll();

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [jobId, router]);

  const progress =
    job && job.total_rows > 0
      ? Math.round((job.processed_rows / job.total_rows) * 100)
      : 0;

  return (
    <section className="rounded-shell border border-line bg-white/84 p-8 shadow-card backdrop-blur">
      <div className="flex flex-col items-center gap-6 text-center">
        {!error && (!job || job.status === "queued" || job.status === "processing") && (
          <>
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-[#f3f0f5] border-t-[#7c3aed]" />
            <div>
              <h2 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                {job ? statusLabel(job.status) : "正在连接..."}
              </h2>
              <p className="mt-2 text-sm text-soft">
                评论正在后台分析，完成后将自动展示结果
              </p>
            </div>
            {job && job.total_rows > 0 && (
              <div className="w-full max-w-sm">
                <div className="flex items-center justify-between text-xs text-soft">
                  <span>已处理 {job.processed_rows} / {job.total_rows} 条</span>
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
                    好评 {job.positive_count} · 差评 {job.negative_count}
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {job?.status === "failed" && (
          <>
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[#fef2f2]">
              <span className="text-2xl">✕</span>
            </div>
            <div>
              <h2 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                分析失败
              </h2>
              <p className="mt-2 text-sm text-[#b44655]">
                {job.error_message || "未知错误，请重试"}
              </p>
            </div>
            <button
              type="button"
              onClick={() => router.push("/upload")}
              className="mt-2 inline-flex min-h-10 items-center justify-center rounded-pill bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-card"
            >
              重新上传
            </button>
          </>
        )}

        {error && !job?.status && (
          <div className="rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm text-[#b44655]">
            {error}
          </div>
        )}
      </div>
    </section>
  );
}
