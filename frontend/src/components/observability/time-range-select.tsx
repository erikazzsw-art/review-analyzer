"use client";

import type { TimeRange } from "./types";
import { cn } from "@/lib/utils";

const OPTIONS: { value: TimeRange; label: string }[] = [
  { value: "1h", label: "1小时" },
  { value: "6h", label: "6小时" },
  { value: "24h", label: "24小时" },
  { value: "7d", label: "7天" },
  { value: "30d", label: "30天" },
];

type TimeRangeSelectProps = {
  value: TimeRange;
  onChange: (v: TimeRange) => void;
};

export function TimeRangeSelect({ value, onChange }: TimeRangeSelectProps) {
  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-line bg-gray-50 p-0.5">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
            value === opt.value
              ? "bg-white text-ink shadow-sm"
              : "text-soft hover:text-ink",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
