"use client";

import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

interface LedgerEntry {
  id: number;
  delta: number;
  reason: string;
  ref_id: string | null;
  balance_after: number;
  created_at: string | null;
}

const REASON_LABEL: Record<string, string> = {
  monthly_grant: "Monthly grant",
  trial: "Trial credits",
  topup: "Top-up",
  refund: "Refund",
  review_analyze: "Review analysis",
  ask: "Ask Reviews",
  insight: "Insight",
  copywriter: "Ad copy",
  translate: "Translation",
  export: "Export",
  competitor: "Competitor analysis",
};

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function CreditLedgerDrawer({ open, onOpenChange }: Props) {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetch("/api/credits/ledger?limit=30", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((d: LedgerEntry[]) => setEntries(Array.isArray(d) ? d : []))
      .catch(() => setEntries([]))
      .finally(() => setLoading(false));
  }, [open]);

  if (!open) return null;
  if (typeof document === "undefined") return null;

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[100] bg-black/30"
        onClick={() => onOpenChange(false)}
      />

      {/* Drawer */}
      <aside className="fixed bottom-0 right-0 top-0 z-[110] flex w-full max-w-sm flex-col border-l border-line bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 className="text-base font-semibold text-ink">Credit History</h2>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded p-1 text-soft hover:bg-line"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded bg-line" />
              ))}
            </div>
          ) : entries.length === 0 ? (
            <p className="mt-8 text-center text-sm text-soft">No transactions yet.</p>
          ) : (
            <ul className="space-y-2">
              {entries.map((e) => {
                const isPositive = e.delta > 0;
                const date = e.created_at
                  ? new Date(e.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })
                  : "";
                return (
                  <li
                    key={e.id}
                    className="flex items-center justify-between rounded-xl border border-line px-3 py-2.5"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-ink">
                        {REASON_LABEL[e.reason] ?? e.reason}
                      </div>
                      <div className="text-[11px] text-soft">
                        {date}
                        {e.ref_id ? ` · ${e.ref_id.slice(0, 8)}` : ""}
                        {" · bal "}{e.balance_after.toLocaleString()}
                      </div>
                    </div>
                    <span
                      className={[
                        "ml-3 shrink-0 text-sm font-semibold",
                        isPositive ? "text-emerald-600" : "text-rose",
                      ].join(" ")}
                    >
                      {isPositive ? "+" : ""}{e.delta.toLocaleString()}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </aside>
    </>,
    document.body,
  );
}
