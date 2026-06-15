"use client";

import * as React from "react";
import { ResponsiveContainer } from "recharts";

import { cn } from "@/lib/utils";

export const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
] as const;

type ChartContainerProps = React.HTMLAttributes<HTMLDivElement> & {
  aspect?: number;
};

export function ChartContainer({
  className,
  children,
  aspect,
  ...props
}: ChartContainerProps) {
  return (
    <div className={cn("w-full", className)} {...props}>
      <ResponsiveContainer width="100%" aspect={aspect} minHeight={200}>
        {children as React.ReactElement}
      </ResponsiveContainer>
    </div>
  );
}

export function ChartTooltipContent({
  active,
  payload,
  label,
  className,
  hideLabel = false,
}: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number | string; color?: string }>;
  label?: string;
  className?: string;
  hideLabel?: boolean;
}) {
  if (!active || !payload?.length) return null;

  return (
    <div
      className={cn(
        "rounded-lg border border-line bg-white px-3 py-2 shadow-card",
        className
      )}
    >
      {!hideLabel && label && (
        <p className="mb-1 text-xs font-medium text-soft">{label}</p>
      )}
      <div className="space-y-0.5">
        {payload.map((entry, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-soft">{entry.name}:</span>
            <span className="font-medium text-ink">{entry.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
