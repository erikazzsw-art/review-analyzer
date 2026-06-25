"use client";

import { cn } from "@/lib/utils";
import type { JobTrace } from "./types";

type Props = { trace: JobTrace };

export function JobTraceDetail({ trace }: Props) {
  const stages = trace.stages || [];
  const totalMs = trace.total_duration_ms || stages.reduce((sum, s) => sum + s.duration_ms, 0) || 1;

  return (
    <div className="space-y-3 border-t border-line bg-gray-50 px-4 py-3">
      {stages.length > 0 ? (
        <>
          <div className="text-xs font-medium text-soft">执行阶段</div>
          <div className="flex h-6 w-full overflow-hidden rounded-full bg-gray-200">
            {stages.map((stage, i) => {
              const pct = (stage.duration_ms / totalMs) * 100;
              if (pct < 0.5) return null;
              const colors = [
                "bg-violet-400",
                "bg-rose-400",
                "bg-emerald-400",
                "bg-amber-400",
                "bg-sky-400",
              ];
              return (
                <div
                  key={i}
                  className={cn("relative h-full", colors[i % colors.length])}
                  style={{ width: `${pct}%` }}
                  title={`${stage.name}: ${stage.duration_ms}ms`}
                />
              );
            })}
          </div>
          <div className="space-y-1">
            {stages.map((stage, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "h-2.5 w-2.5 rounded-sm",
                      ["bg-violet-400", "bg-rose-400", "bg-emerald-400", "bg-amber-400", "bg-sky-400"][i % 5],
                    )}
                  />
                  <span className="text-ink">{stage.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-soft">{stage.duration_ms}ms</span>
                  {stage.error && (
                    <span className="text-red-600">{stage.error}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="text-xs text-soft">无阶段追踪数据</div>
      )}

      {trace.error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {trace.error}
        </div>
      )}
    </div>
  );
}
