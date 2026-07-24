"use client";

import { useMemo, useState } from "react";

import { updateReviewTracker } from "@/lib/api/browser";
import type { ReviewTracker } from "@/lib/api/types";

type ReviewTrackerPanelProps = {
  items: ReviewTracker[];
};

const STATUS_OPTIONS = [
  { value: "pending", label: "待复盘" },
  { value: "improved", label: "已改善" },
  { value: "not_improved", label: "未改善" },
  { value: "follow_up", label: "继续跟进" },
  { value: "done", label: "已完结" },
];

export function ReviewTrackerPanel({ items }: ReviewTrackerPanelProps) {
  const [activeStatus, setActiveStatus] = useState("all");
  const [selectedTrackerId, setSelectedTrackerId] = useState<number | null>(items[0]?.id ?? null);
  const [reviewScope, setReviewScope] = useState("");
  const [currentPct, setCurrentPct] = useState("");
  const [resultStatus, setResultStatus] = useState("pending");
  const [conclusion, setConclusion] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  const filteredItems = useMemo(
    () => (activeStatus === "all" ? items : items.filter((item) => item.result_status === activeStatus)),
    [activeStatus, items],
  );

  const selectedTracker = filteredItems.find((item) => item.id === selectedTrackerId) || filteredItems[0] || null;

  async function handleSave(): Promise<void> {
    if (!selectedTracker) {
      return;
    }
    setError("");
    setMessage("");
    setIsBusy(true);
    try {
      await updateReviewTracker(selectedTracker.id, {
        reviewScope: reviewScope.trim() || null,
        currentPct: currentPct.trim() ? Number(currentPct) : null,
        resultStatus,
        conclusion: conclusion.trim() || null,
      });
      setMessage("复盘结果已保存。");
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "保存失败");
    } finally {
      setIsBusy(false);
    }
  }

  if (items.length === 0) {
    return (
      <section className="rounded-shell border border-dashed border-line bg-white/80 px-6 py-10 shadow-card backdrop-blur">
        <h2 className="font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          暂无复盘追踪
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-soft">
          先从行动中心把事项加入复盘，再回来填写前后占比和结论。
        </p>
      </section>
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setActiveStatus("all")}
            className={[
              "rounded-pill border px-4 py-2 text-sm font-semibold",
              activeStatus === "all" ? "border-transparent bg-ink text-white shadow-card" : "border-line bg-white text-soft",
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
                activeStatus === item.value ? "border-transparent bg-ink text-white shadow-card" : "border-line bg-white text-soft",
              ].join(" ")}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="mt-5 space-y-3">
          {filteredItems.map((item) => {
            const isSelected = item.id === selectedTrackerId;
            return (
              <button
                type="button"
                key={item.id}
                onClick={() => {
                  setSelectedTrackerId(item.id);
                  setReviewScope(item.review_scope || "");
                  setCurrentPct(item.current_pct == null ? "" : String(item.current_pct));
                  setResultStatus(item.result_status);
                  setConclusion(item.conclusion || "");
                }}
                className={[
                  "w-full rounded-card border px-4 py-4 text-left transition",
                  isSelected ? "border-transparent bg-ink text-white shadow-card" : "border-line bg-white hover:border-[#f36f8f]",
                ].join(" ")}
              >
                <div className="text-sm font-semibold">{item.tracker_title}</div>
                <div className={["mt-2 text-xs leading-6", isSelected ? "text-white/80" : "text-soft"].join(" ")}>
                  {item.parent_product_id || item.source_product_id || "未绑定产品"} · {item.specific_issue || item.tag_name || "—"}
                </div>
                <div className={["mt-1 text-xs leading-6", isSelected ? "text-white/80" : "text-soft"].join(" ")}>
                  {item.result_status} · {item.current_pct == null ? "—" : `${item.current_pct.toFixed(1)}%`}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        {selectedTracker ? (
          <>
            <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
              FOLLOW-UP TRACKING
            </div>
            <h2 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              {selectedTracker.tracker_title}
            </h2>
            <p className="mt-2 text-sm leading-7 text-soft">
              {selectedTracker.improvement_action || "暂无改进动作。"}
            </p>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-sm font-semibold text-ink">复盘范围</span>
                <input
                  value={reviewScope}
                  onChange={(event) => setReviewScope(event.target.value)}
                  className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
                />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-semibold text-ink">当前占比</span>
                <input
                  value={currentPct}
                  onChange={(event) => setCurrentPct(event.target.value)}
                  className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
                />
              </label>
              <label className="space-y-2 md:col-span-2">
                <span className="text-sm font-semibold text-ink">结论状态</span>
                <select
                  value={resultStatus}
                  onChange={(event) => setResultStatus(event.target.value)}
                  className="w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
                >
                  {STATUS_OPTIONS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-2 md:col-span-2">
                <span className="text-sm font-semibold text-ink">复盘结论</span>
                <textarea
                  value={conclusion}
                  onChange={(event) => setConclusion(event.target.value)}
                  className="min-h-28 w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
                />
              </label>
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                disabled={isBusy}
                onClick={handleSave}
                className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card disabled:opacity-60"
              >
                保存复盘结果
              </button>
              <div className="rounded-card border border-line bg-[#fffafb] px-4 py-3 text-sm leading-7 text-soft">
                初始占比：{selectedTracker.baseline_pct == null ? "—" : `${selectedTracker.baseline_pct.toFixed(1)}%`}
              </div>
            </div>
          </>
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
