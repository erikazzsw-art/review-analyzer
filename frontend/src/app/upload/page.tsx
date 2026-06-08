"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app/app-shell";
import { submitUploadJob, fetchUploadJob } from "@/lib/api/browser";
import type { UploadJob } from "@/lib/api/types";

const workflowPurposes = [
  "竞品调研",
  "新品上线监控",
  "日常评论分析",
  "Listing 优化",
  "质量问题复盘",
  "版本改版验证",
];

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

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<UploadJob | null>(null);
  const [error, setError] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [form, setForm] = useState<FormState>({
    productId: "",
    productName: "",
    platform: "Amazon",
    category: "家具家居",
    version: "V1",
    workflowPurpose: "日常评论分析",
    dateStart: "",
    dateEnd: "",
    versionNotes: "",
  });

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
        setError(candidate.message || "任务状态轮询失败");
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
      setError("请先选择文件并补全产品编号、版本和工作目的。");
      return;
    }

    setError("");
    setIsSubmitting(true);
    try {
      const response = await submitUploadJob({
        sourceFile: file,
        productId: form.productId.trim(),
        version: form.version.trim(),
        workflowPurpose: form.workflowPurpose.trim(),
        productName: form.productName.trim(),
        platform: form.platform.trim(),
        category: form.category.trim(),
        dateStart: form.dateStart.trim(),
        dateEnd: form.dateEnd.trim(),
        versionNotes: form.versionNotes.trim(),
      });
      setJob(response.job);
      if (response.job.status === "done" && response.job.session_id) {
        router.push(`/analysis/results?session_id=${response.job.session_id}`);
      }
    } catch (submitError) {
      const candidate = submitError as { message?: string };
      setError(candidate.message || "上传任务创建失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppShell
      currentPath="/upload"
      title="先上传评论，再让系统自动排队分析。"
      description="这一页把上传文件、创建分析任务和轮询状态连成一条清晰的操作链。你提交后会先看到任务进入队列，完成后自动跳到结果页。"
    >
      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
            STEP 1
          </div>
          <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
            上传评论文件
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-soft">
            先选文件，再填产品编号与工作目的。后台会自动创建分析任务并开始处理。
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">产品编号</span>
              <input
                value={form.productId}
                onChange={(event) =>
                  setForm((current) => ({ ...current, productId: event.target.value }))
                }
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
                placeholder="例如：SKU-1001"
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">产品名称</span>
              <input
                value={form.productName}
                onChange={(event) =>
                  setForm((current) => ({ ...current, productName: event.target.value }))
                }
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
                placeholder="例如：无线蓝牙耳机"
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">平台</span>
              <input
                value={form.platform}
                onChange={(event) =>
                  setForm((current) => ({ ...current, platform: event.target.value }))
                }
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">类目</span>
              <input
                value={form.category}
                onChange={(event) =>
                  setForm((current) => ({ ...current, category: event.target.value }))
                }
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">版本号</span>
              <input
                value={form.version}
                onChange={(event) =>
                  setForm((current) => ({ ...current, version: event.target.value }))
                }
                className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">工作目的</span>
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
                {workflowPurposes.map((purpose) => (
                  <option key={purpose} value={purpose}>
                    {purpose}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-ink">开始日期</span>
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
              <span className="text-sm font-semibold text-ink">结束日期</span>
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
            <span className="text-sm font-semibold text-ink">版本说明</span>
            <textarea
              value={form.versionNotes}
              onChange={(event) =>
                setForm((current) => ({ ...current, versionNotes: event.target.value }))
              }
              className="min-h-28 w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
              placeholder="可选，例如：本轮更新了包装与材质..."
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
                <span className="text-sm font-semibold text-ink">选择评论文件</span>
                <span className="text-sm leading-7 text-soft">
                  支持 CSV、XLSX、DOCX、TXT。选择后会自动创建任务并开始分析。
                </span>
                <span className="inline-flex w-fit rounded-pill bg-white px-4 py-2 text-xs font-semibold text-soft">
                  {file ? file.name : "尚未选择文件"}
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
              {isSubmitting ? "提交中..." : "上传并开始分析"}
            </button>
            <button
              type="button"
              onClick={() => router.push("/workspace")}
              className="inline-flex min-h-12 items-center justify-center rounded-pill border border-line bg-white px-6 py-3 text-sm font-semibold text-ink transition hover:bg-[#fffafb]"
            >
              返回工作台
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
            <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
              STEP 2
            </div>
            <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              任务状态
            </h3>
            <div className="mt-4 space-y-4">
              {job ? (
                <>
                  <div className="flex items-center justify-between rounded-card border border-line bg-white px-4 py-4">
                    <span className="text-sm font-semibold text-ink">当前状态</span>
                    <span className={`rounded-pill px-3 py-1 text-xs font-bold ${statusTone(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="rounded-card border border-line bg-[#fffafb] px-4 py-4">
                      <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                        已处理
                      </div>
                      <div className="mt-2 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
                        {job.processed_rows}/{job.total_rows}
                      </div>
                    </div>
                    <div className="rounded-card border border-line bg-[#fbf9ff] px-4 py-4">
                      <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                        结果摘要
                      </div>
                      <div className="mt-2 text-sm leading-7 text-soft">
                        正面 {job.positive_count} · 负面 {job.negative_count}
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
                      ? "任务正在后台分析，页面会自动轮询状态。"
                      : job.status === "done"
                        ? "任务已完成，正在准备跳转到结果页。"
                        : job.status === "failed"
                          ? "任务失败，请检查上传文件或后端日志。"
                          : "任务已创建，等待后台开始处理。"}
                  </div>
                </>
              ) : (
                <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-6 text-sm leading-7 text-soft">
                  提交文件后，这里会显示任务状态、处理进度和结果摘要。
                </div>
              )}
            </div>
          </section>

          <section className="rounded-shell border border-line bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(252,246,251,0.94))] p-6 shadow-card backdrop-blur">
            <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              这次上传会做什么
            </h3>
            <div className="mt-4 space-y-3 text-sm leading-7 text-soft">
              <div className="rounded-card border border-line bg-white px-4 py-4">
                1. 解析文件，提取评论内容、日期和评分。
              </div>
              <div className="rounded-card border border-line bg-white px-4 py-4">
                2. 创建后台 job，先进入队列，再逐条分析。
              </div>
              <div className="rounded-card border border-line bg-white px-4 py-4">
                3. 分析完成后自动跳转到结果页，继续看证据和结论。
              </div>
            </div>
          </section>
        </div>
      </section>
    </AppShell>
  );
}
