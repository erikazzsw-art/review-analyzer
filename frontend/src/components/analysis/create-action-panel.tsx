"use client";

import { useMemo, useState } from "react";

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

const OWNER_OPTIONS = ["运营", "产研", "质检", "复盘"] as const;

export function CreateActionPanel({
  sessionId,
  productId,
  sourceProductId,
  sourceVersion,
  sourceBatchLabel,
  candidates,
}: CreateActionPanelProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [title, setTitle] = useState("");
  const [ownerRole, setOwnerRole] = useState("运营");
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
      setError("没有可用的问题候选项。");
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
      setSuccess("行动已创建。去行动中心可以继续推进状态。");
      setTitle("");
      setSuggestedAction("");
      setExpectedReviewAt("");
      setExpectedEffectBatch("");
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "创建行动失败");
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
            CREATE ACTION
          </div>
          <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            从这批结果直接创建行动
          </h3>
          <p className="mt-2 text-sm leading-7 text-soft">
            把 TOP 问题变成团队事项，再在行动中心和复盘追踪里继续推进。
          </p>
        </div>
        <div className="rounded-card border border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
          来源：{sourceProductId} · {sourceVersion} · {sourceBatchLabel}
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">选择问题</span>
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
          <span className="text-sm font-semibold text-ink">行动标题</span>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder={selectedCandidate?.label || "例如：安装问题处理"}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          />
        </label>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">责任角色</span>
          <select
            value={ownerRole}
            onChange={(event) => setOwnerRole(event.target.value)}
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          >
            {OWNER_OPTIONS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">预计复盘时间</span>
          <input
            value={expectedReviewAt}
            onChange={(event) => setExpectedReviewAt(event.target.value)}
            placeholder="例如：2026-06-15"
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          />
        </label>
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">预计生效批次</span>
          <input
            value={expectedEffectBatch}
            onChange={(event) => setExpectedEffectBatch(event.target.value)}
            placeholder="例如：V2 / 下一批"
            className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          />
        </label>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <label className="space-y-2">
          <span className="text-sm font-semibold text-ink">建议动作</span>
          <textarea
            value={suggestedAction}
            onChange={(event) => setSuggestedAction(event.target.value)}
            placeholder={selectedCandidate?.suggestedAction || selectedCandidate?.detail || ""}
            className="min-h-28 w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
          />
        </label>
        <div className="space-y-3">
          <label className="space-y-2">
            <span className="text-sm font-semibold text-ink">初始状态</span>
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            >
              <option value="todo">待处理</option>
              <option value="in_progress">处理中</option>
              <option value="pending_review">待复盘</option>
              <option value="done">已完结</option>
            </select>
          </label>
          <div className="rounded-card border border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
            选中的问题：{selectedCandidate?.label || "—"}
            <br />
            占比参考：{selectedCandidate?.currentPct == null ? "—" : `${selectedCandidate.currentPct.toFixed(1)}%`}
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="text-sm leading-7 text-soft">
          {selectedCandidate?.detail || "选一个问题后，把它交给对应角色。"}
        </div>
        <button
          type="button"
          onClick={handleCreate}
          disabled={isSubmitting}
          className="inline-flex min-h-12 items-center justify-center rounded-pill bg-ink px-6 py-3 text-sm font-semibold text-white shadow-card transition disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "创建中..." : "创建行动"}
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
