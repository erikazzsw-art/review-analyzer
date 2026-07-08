"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { createActionItem } from "@/lib/api/browser";
import type { ActionItemCreatePayload } from "@/lib/api/types";

type IssueCandidate = {
  label: string;
  detail: string;
  currentPct?: number | null;
  suggestedAction?: string | null;
};

type CreateActionPanelProps = {
  sessionId?: number;
  productId?: number | null;
  sourceProductId: string;
  sourceVersion: string;
  sourceBatchLabel: string;
  candidates: IssueCandidate[];
};

// API 契约：owner_role 后端存中文（workers/jobs.py 默认 "运营"、action_advisor 走 get_dept_label 也返回中文），
// 前端必须继续发中文值以避免混合语言环境下的聚合/查询错乱。UI 只对显示做 i18n。
// 完整迁移到 role slug 是独立任务（等 backend migration）。
const OWNER_ROLES = [
  { value: "运营", labelKey: "ownerOps" },
  { value: "产研", labelKey: "ownerProduct" },
  { value: "质检", labelKey: "ownerQA" },
  { value: "复盘", labelKey: "ownerReview" },
] as const;

export function CreateActionPanel({
  sessionId,
  productId,
  sourceProductId,
  sourceVersion,
  sourceBatchLabel,
  candidates,
}: CreateActionPanelProps) {
  const t = useTranslations("analysis.action");
  const tCommon = useTranslations("common");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [title, setTitle] = useState("");
  const [ownerRole, setOwnerRole] = useState<string>(OWNER_ROLES[0].value);
  const [suggestedAction, setSuggestedAction] = useState("");
  const [expectedReviewAt, setExpectedReviewAt] = useState("");
  const [expectedEffectBatch, setExpectedEffectBatch] = useState("");
  const [status, setStatus] = useState("todo");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedCandidate = useMemo(() => candidates[selectedIndex] || null, [candidates, selectedIndex]);

  async function handleCreate(): Promise<void> {
    if (!selectedCandidate) {
      setError(t("noCandidates"));
      return;
    }

    const finalTitle = title.trim() || selectedCandidate.label;
    const finalAction = suggestedAction.trim() || selectedCandidate.suggestedAction || selectedCandidate.detail;

    setError("");
    setSuccess("");
    setIsSubmitting(true);
    try {
      await createActionItem({
        productId: productId ?? null,
        sessionId: sessionId ?? null,
        sourceProductId,
        sourceVersion,
        sourceBatchLabel,
        title: finalTitle,
        tagName: selectedCandidate.label,
        currentPct: selectedCandidate.currentPct ?? null,
        ownerRole,
        suggestedAction: finalAction,
        expectedReviewAt: expectedReviewAt.trim() || null,
        expectedEffectBatch: expectedEffectBatch.trim() || null,
        status,
      } satisfies ActionItemCreatePayload);
      setSuccess(t("createSuccess"));
      setTitle("");
      setSuggestedAction("");
      setExpectedReviewAt("");
      setExpectedEffectBatch("");
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || t("createFail"));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (candidates.length === 0) {
    return null;
  }

  return (
    <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            {t("dashboardBadge")}
          </div>
          <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            {t("dashboardTitle")}
          </h3>
          <p className="mt-2 text-sm leading-7 text-soft">
            {t("dashboardSubtitle")}
          </p>
        </div>
        <div className="rounded-card border border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
          {t("sourceFormat", {
            productId: sourceProductId,
            version: sourceVersion,
            label: sourceBatchLabel,
          })}
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">{t("chooseIssue")}</span>
          <select
            value={selectedIndex}
            onChange={(event) => setSelectedIndex(Number(event.target.value))}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          >
            {candidates.map((item, index) => (
              <option key={`${item.label}-${index}`} value={index}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">{t("actionTitle")}</span>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder={selectedCandidate?.label || t("actionTitlePlaceholder")}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          />
        </label>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">{t("ownerRole")}</span>
          <select
            value={ownerRole}
            onChange={(event) => setOwnerRole(event.target.value)}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          >
            {OWNER_ROLES.map((item) => (
              <option key={item.value} value={item.value}>
                {t(item.labelKey)}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">{t("expectedReviewAt")}</span>
          <input
            value={expectedReviewAt}
            onChange={(event) => setExpectedReviewAt(event.target.value)}
            placeholder={t("expectedReviewPlaceholder")}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          />
        </label>
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">{t("expectedEffectBatch")}</span>
          <input
            value={expectedEffectBatch}
            onChange={(event) => setExpectedEffectBatch(event.target.value)}
            placeholder={t("expectedEffectBatchPlaceholder")}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          />
        </label>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">{t("suggestedAction")}</span>
          <textarea
            value={suggestedAction}
            onChange={(event) => setSuggestedAction(event.target.value)}
            placeholder={selectedCandidate?.suggestedAction || selectedCandidate?.detail || ""}
            className="min-h-28 w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          />
        </label>
        <div className="space-y-3">
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">{t("initialStatus")}</span>
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            >
              <option value="todo">{t("statusTodo")}</option>
              <option value="in_progress">{t("statusInProgress")}</option>
              <option value="pending_review">{t("statusPendingReview")}</option>
              <option value="done">{t("statusDone")}</option>
            </select>
          </label>
          <div className="rounded-card border border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
            {t("selectedIssueLabel", { label: selectedCandidate?.label || "—" })}
            <br />
            {t("ratioReferenceLabel", {
              pct:
                selectedCandidate?.currentPct == null
                  ? "—"
                  : `${selectedCandidate.currentPct.toFixed(1)}%`,
            })}
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="text-sm leading-7 text-soft">
          {selectedCandidate?.detail || t("dashHint")}
        </div>
        <button
          type="button"
          onClick={handleCreate}
          disabled={isSubmitting}
          className="inline-flex min-h-12 items-center justify-center rounded-pill bg-ink px-6 py-3 text-sm font-semibold text-white shadow-card transition disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? tCommon("creating") : t("createBtn")}
        </button>
      </div>

      {error ? (
        <div className="mt-4 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]">
          {error}
        </div>
      ) : null}
      {success ? (
        <div className="mt-4 rounded-card border border-[#c9e8dc] bg-[#f6fffb] px-4 py-3 text-sm leading-7 text-[#3d8b74]">
          {success}
        </div>
      ) : null}
    </section>
  );
}
