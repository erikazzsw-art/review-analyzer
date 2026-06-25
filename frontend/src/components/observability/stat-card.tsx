"use client";

import { cn } from "@/lib/utils";

type StatCardProps = {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "default" | "danger" | "success";
};

export function StatCard({ label, value, sub, accent = "default" }: StatCardProps) {
  return (
    <div className="rounded-xl border border-line bg-white p-4">
      <div className="text-xs text-soft">{label}</div>
      <div
        className={cn(
          "mt-1 text-2xl font-bold",
          accent === "danger" && "text-red-600",
          accent === "success" && "text-emerald-600",
          accent === "default" && "text-ink",
        )}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-soft">{sub}</div>}
    </div>
  );
}
