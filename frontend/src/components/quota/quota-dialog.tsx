"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { Info } from "lucide-react";
import { useTranslations } from "next-intl";

import { openBillingCheckout } from "@/lib/billing";
import type { QuotaItem } from "@/lib/api/server";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  DIMENSION_HINT_KEY,
  DIMENSION_LABEL_KEY,
  PLAN_LABEL_KEY,
  QUOTA_GROUPS,
  nextResetDate,
} from "./quota-groups";

type QuotaDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  items: QuotaItem[];
};

export function QuotaDialog({ open, onOpenChange, items }: QuotaDialogProps) {
  const t = useTranslations("quotaDialog");
  const plan = items[0]?.plan ?? "free";
  const planLabel = t(PLAN_LABEL_KEY[plan] ?? "plans.free");
  const resetDate = nextResetDate();

  const byDimension = new Map<string, QuotaItem>();
  for (const item of items) {
    if (!item.error) {
      byDimension.set(item.dimension, item);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] max-w-[560px] gap-0 overflow-hidden rounded-shell border-line bg-white p-0 shadow-card">
        <DialogHeader className="space-y-1.5 border-b border-line px-6 pb-4 pt-6">
          <DialogTitle className="font-heading text-xl font-extrabold tracking-[-0.03em] text-ink">
            {t("title")}
          </DialogTitle>
          <p className="text-xs text-soft">
            {t("currentPlan")}: {planLabel} · {t("resetNotice", { date: resetDate })}
          </p>
        </DialogHeader>

        <div className="max-h-[60vh] overflow-y-auto px-6 py-5">
          <TooltipProvider delayDuration={150}>
            <div className="space-y-4">
              {QUOTA_GROUPS.map((group) => {
                const groupItems = group.dimensions
                  .map((dim) => byDimension.get(dim))
                  .filter((item): item is QuotaItem => Boolean(item));

                if (groupItems.length === 0) return null;

                return (
                  <section
                    key={group.key}
                    className="rounded-card border border-line bg-white/70 px-4 py-3"
                  >
                    <h4 className="mb-3 text-sm font-semibold text-ink">
                      {t(group.titleKey)}
                    </h4>
                    <ul className="space-y-3">
                      {groupItems.map((item) => (
                        <QuotaRow key={item.dimension} item={item} />
                      ))}
                    </ul>
                  </section>
                );
              })}
            </div>
          </TooltipProvider>
        </div>

        {plan === "free" && (
          <div className="border-t border-line bg-[#f8f6f3] px-6 py-4">
            <Link
              href="/pricing"
              onClick={() => onOpenChange(false)}
              className="inline-flex w-full items-center justify-center rounded-pill bg-[#d94d72] px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:bg-[#c4405f]"
            >
              {t("upgrade")}
            </Link>
          </div>
        )}

        {plan === "pro" && (
          <div className="border-t border-line bg-[#f8f6f3] px-6 py-4">
            <ManageSubscriptionButton onDone={() => onOpenChange(false)} />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function QuotaRow({ item }: { item: QuotaItem }) {
  const t = useTranslations("quotaDialog");
  const label = t(DIMENSION_LABEL_KEY[item.dimension] ?? "");
  const hintKey = DIMENSION_HINT_KEY[item.dimension];
  const hint = hintKey ? t(hintKey) : "";
  const unit = item.unit ?? "";
  const isUnlimited = item.unlimited || item.limit === -1;
  const period = item.period;
  const used = item.used ?? 0;
  const limit = item.limit;
  const pct = isUnlimited || !limit ? 0 : Math.min((used / limit) * 100, 100);
  const isHigh = !isUnlimited && pct >= 80;

  const showProgress =
    !isUnlimited && (period === "monthly" || period === "daily" || period === "forever");

  let rightSlot: React.ReactNode;
  if (isUnlimited) {
    rightSlot = <span className="text-sm text-soft">{t("unlimited")}</span>;
  } else if (period === "per_request") {
    rightSlot = (
      <span className="text-sm font-semibold text-ink tabular-nums">
        {limit} {unit}
      </span>
    );
  } else {
    rightSlot = (
      <span
        className={[
          "text-sm font-semibold tabular-nums",
          isHigh ? "text-[#d94d72]" : "text-ink",
        ].join(" ")}
      >
        {used} / {limit} {unit}
      </span>
    );
  }

  return (
    <li>
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="truncate text-sm text-ink">{label}</span>
          {hint && (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  aria-label={label}
                  className="inline-flex h-4 w-4 items-center justify-center text-soft/70 hover:text-soft"
                >
                  <Info size={13} />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-[240px] text-xs">
                {hint}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        {rightSlot}
      </div>
      {showProgress && (
        <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-[#f0f0f0]">
          <div
            className={[
              "h-full rounded-full transition-all",
              isHigh ? "bg-[#d94d72]" : "bg-[#4a7dc7]",
            ].join(" ")}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </li>
  );
}

function ManageSubscriptionButton({ onDone }: { onDone: () => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const checkoutRef = useRef<HTMLDivElement | null>(null);

  async function handleManage() {
    setError(""); setLoading(true);
    try {
      const result = await openBillingCheckout(checkoutRef.current, "pro", "monthly");
      if (!result.configured || !result.hasHtml) {
        onDone();
        return;
      }
    } catch (err) {
      setError((err as { message?: string }).message || "操作失败");
    } finally { setLoading(false); }
  }

  return (
    <>
      <div ref={checkoutRef} className="hidden" aria-hidden="true" />
      <button
        type="button"
        onClick={handleManage}
        disabled={loading}
        className="inline-flex w-full items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-ink shadow-sm transition hover:bg-[#f8f6f3] disabled:opacity-50"
      >
        {loading ? "加载中..." : "管理订阅"}
      </button>
      {error && <p className="mt-2 text-center text-xs text-red-600">{error}</p>}
    </>
  );
}
