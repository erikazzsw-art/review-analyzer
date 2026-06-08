"use client";

import { useMemo, useState } from "react";

import { createTrackerFromAction, updateActionStatus } from "@/lib/api/browser";
import type { ActionItem, ReviewTracker } from "@/lib/api/types";

type ActionCenterPanelProps = {
  items: ActionItem[];
};

const STATUS_OPTIONS = [
  { value: "todo", label: "待处理" },
  { value: "in_progress", label: "处理中" },
  { value: "pending_review", label: "待复盘" },
  { value: "done", label: "已完结" },
];

export function ActionCenterPanel({ items }: ActionCenterPanelProps) {
  const [activeStatus, setActiveStatus] = useState("all");
  const [selectedActionId, setSelectedActionId] = useState<number | null>(items[0]?.id ?? null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  const filteredItems = useMemo(
    () => (activeStatus === "all" ? items : items.filter((item) => item.status === activeStatus)),
    [activeStatus, items],
  );

  const selectedAction = filteredItems.find((item) => item.id === selectedActionId) || filteredItems[0] || null;

  async function handleStatusChange(actionId: number, status: string): Promise<void> {
    setError("");
    setMessage("");
    setIsBusy(true);
    try {
      await updateActionStatus(actionId, status);
      setMessage("状态已更新。");
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "状态更新失败");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCreateTracker(action: ActionItem): Promise<void> {
    setError("");
    setMessage("");
    setIsBusy(true);
    try {
      const response = await createTrackerFromAction(action.id, {
        actionItemId: action.id,
        productId: action.product_id ?? null,
        variantId: action.variant_id ?? null,
        trackerTitle: `${action.tag_name || action.title} 复盘`,
        tagName: action.tag_name ?? null,
        baselinePct: action.current_pct ?? null,
        improvementAction: action.suggested_action ?? null,
        effectiveBatch: action.expected_effect_batch ?? null,
        reviewScope: action.expected_review_at ?? null,
        currentPct: null,
        resultStatus: "pending",
        conclusion: null,
      });
      setMessage(`已创建复盘追踪：${response.tracker.tracker_title}`);
      setSelectedActionId(response.action.id);
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "创建复盘失败");
    } finally {
      setIsBusy(false);
    }
  }

  if (items.length === 0) {
    return (
      <section className="rounded-shell border border-dashed border-line bg-white/80 px-6 py-10 shadow-card backdrop-blur">
        <h2 className="font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          暂无行动事项
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-soft">
          先去分析结果页从 TOP 问题创建一个 action，或者从工作台里继续推进现有事项。
        </p>
      </section>
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_1.1fr]">
      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
              ACTION CENTER
            </div>
            <h2 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              行动中心
            </h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setActiveStatus("all")}
              className={[
                "rounded-pill border px-4 py-2 text-sm font-semibold",
                activeStatus === "all"
                  ? "border-transparent bg-ink text-white shadow-card"
                  : "border-line bg-white text-soft",
              ].join(" ")}
            >
              全部
            </button>
            {STATUS_OPTIONS.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => setActiveStatus(item.value)}
                className={[
                  "rounded-pill border px-4 py-2 text-sm font-semibold",
                  activeStatus === item.value
                    ? "border-transparent bg-ink text-white shadow-card"
                    : "border-line bg-white text-soft",
                ].join(" ")}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-5 space-y-3">
          {filteredItems.map((item) => {
            const isSelected = item.id === selectedActionId;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelectedActionId(item.id)}
                className={[
                  "w-full rounded-card border px-4 py-4 text-left transition",
                  isSelected ? "border-transparent bg-ink text-white shadow-card" : "border-line bg-white hover:border-[#f36f8f]",
                ].join(" ")}
              >
                <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="text-sm font-semibold">{item.title}</div>
                    <div className={["mt-2 text-xs leading-6", isSelected ? "text-white/80" : "text-soft"].join(" ")}>
                      {item.source_product_id || item.parent_product_id || "未绑定产品"} · {item.source_version || "V1"} · {item.source_batch_label || "未记录"}
                    </div>
                  </div>
                  <div className={["text-xs font-semibold uppercase tracking-[0.12em]", isSelected ? "text-white/80" : "text-soft"].join(" ")}>
                    {item.status}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        {selectedAction ? (
          <div>
            <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
              CURRENT ACTION
            </div>
            <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              {selectedAction.title}
            </h3>
            <p className="mt-2 text-sm leading-7 text-soft">
              {selectedAction.suggested_action || "暂无建议动作。"}
            </p>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div className="rounded-card border border-line bg-white px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">问题标签</div>
                <div className="mt-2 text-sm leading-7 text-ink">{selectedAction.tag_name || "—"}</div>
              </div>
              <div className="rounded-card border border-line bg-white px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">当前占比</div>
                <div className="mt-2 text-sm leading-7 text-ink">
                  {selectedAction.current_pct == null ? "—" : `${selectedAction.current_pct.toFixed(1)}%`}
                </div>
              </div>
              <div className="rounded-card border border-line bg-white px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">责任角色</div>
                <div className="mt-2 text-sm leading-7 text-ink">{selectedAction.owner_role || "—"}</div>
              </div>
              <div className="rounded-card border border-line bg-white px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">预计复盘</div>
                <div className="mt-2 text-sm leading-7 text-ink">{selectedAction.expected_review_at || "—"}</div>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                disabled={isBusy}
                onClick={() => handleStatusChange(selectedAction.id, "in_progress")}
                className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card disabled:opacity-60"
              >
                标记处理中
              </button>
              <button
                type="button"
                disabled={isBusy}
                onClick={() => handleStatusChange(selectedAction.id, "pending_review")}
                className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-ink disabled:opacity-60"
              >
                标记待复盘
              </button>
              <button
                type="button"
                disabled={isBusy}
                onClick={() => handleStatusChange(selectedAction.id, "done")}
                className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-ink disabled:opacity-60"
              >
                标记已完结
              </button>
              <button
                type="button"
                disabled={isBusy}
                onClick={() => handleCreateTracker(selectedAction)}
                className="inline-flex min-h-11 items-center justify-center rounded-pill bg-[#f36f8f] px-5 py-3 text-sm font-semibold text-white shadow-card disabled:opacity-60"
              >
                加入复盘
              </button>
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="mt-5 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]">
            {error}
          </div>
        ) : null}
        {message ? (
          <div className="mt-5 rounded-card border border-[#c9e8dc] bg-[#f6fffb] px-4 py-3 text-sm leading-7 text-[#3d8b74]">
            {message}
          </div>
        ) : null}
      </section>
    </div>
  );
}
