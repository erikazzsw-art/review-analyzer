"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import type { ModelStatus } from "./types";
import { fetchAnalytics } from "./types";

export function ModelStatusRow() {
  const [models, setModels] = useState<ModelStatus | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;

    function load() {
      fetchAnalytics<ModelStatus>("model-status")
        .then(setModels)
        .catch(() => {});
    }

    load();
    timer = setInterval(load, 60_000);
    return () => clearInterval(timer);
  }, []);

  if (!models) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {Object.entries(models.models).map(([name, info]) => {
        const isOpen = info.circuit_open;
        const isOk = info.available && !isOpen;
        return (
          <div
            key={name}
            className={cn(
              "flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
              isOpen && "border-red-200 bg-red-50 text-red-700",
              !isOpen && isOk && "border-emerald-200 bg-emerald-50 text-emerald-700",
              !isOpen && !isOk && "border-yellow-200 bg-yellow-50 text-yellow-700",
            )}
          >
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                isOpen && "bg-red-500",
                !isOpen && isOk && "bg-emerald-500",
                !isOpen && !isOk && "bg-yellow-500",
              )}
            />
            {name}
            {info.consecutive_failures > 0 && (
              <span className="text-[10px] opacity-70">
                ({info.consecutive_failures})
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
