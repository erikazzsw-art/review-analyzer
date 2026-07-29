"use client";

import { cn } from "@/lib/utils";
import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { MetricStatus } from "./metric-status";
import { METRIC_STATUS_LABELS } from "./metric-status";

type StatCardProps = {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "default" | "danger" | "success" | "warning";
  status?: MetricStatus;
  description?: string;
  normalRange?: string;
  actionHint?: string;
};

const STATUS_STYLES: Record<MetricStatus, string> = {
  normal: "border-emerald-200 bg-emerald-50 text-emerald-700",
  attention: "border-amber-200 bg-amber-50 text-amber-700",
  abnormal: "border-orange-200 bg-orange-50 text-orange-700",
  critical: "border-red-200 bg-red-50 text-red-700",
};

export function StatCard({
  label,
  value,
  sub,
  accent = "default",
  status,
  description,
  normalRange,
  actionHint,
}: StatCardProps) {
  const hasExplanation = description || normalRange || actionHint;

  return (
    <div className="rounded-xl border border-line bg-white p-4">
      <div className="flex min-h-5 items-center justify-between gap-2">
        <div className="flex items-center gap-1 text-xs text-soft">
          <span>{label}</span>
          {hasExplanation && (
            <TooltipProvider delayDuration={150}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="rounded-full text-soft transition-colors hover:text-ink focus:outline-none focus:ring-2 focus:ring-primary/30"
                    aria-label={`${label}说明`}
                  >
                    <Info className="h-3.5 w-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-[280px] bg-ink text-white">
                  <div className="space-y-1">
                    {description && <p>{description}</p>}
                    {normalRange && <p>正常范围：{normalRange}</p>}
                    {actionHint && <p>异常后：{actionHint}</p>}
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
        {status && (
          <span
            className={cn(
              "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium",
              STATUS_STYLES[status],
            )}
          >
            {METRIC_STATUS_LABELS[status]}
          </span>
        )}
      </div>
      <div
        className={cn(
          "mt-1 text-2xl font-bold",
          accent === "danger" && "text-red-600",
          accent === "success" && "text-emerald-600",
          accent === "warning" && "text-amber-600",
          accent === "default" && "text-ink",
        )}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-soft">{sub}</div>}
    </div>
  );
}
