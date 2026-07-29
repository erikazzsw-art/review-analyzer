"use client";

import type { TimeRange } from "./types";
import { timeRangeToWindowHours } from "./types";

export type MetricStatus = "normal" | "attention" | "abnormal" | "critical";

export const METRIC_STATUS_LABELS: Record<MetricStatus, string> = {
  normal: "正常",
  attention: "注意",
  abnormal: "异常",
  critical: "严重",
};

export function getErrorRateStatus(errorRate: number): MetricStatus {
  if (errorRate >= 20) return "critical";
  if (errorRate >= 10) return "abnormal";
  if (errorRate >= 5) return "attention";
  return "normal";
}

export function getP95LatencyStatus(p95Ms: number): MetricStatus {
  if (p95Ms >= 30_000) return "critical";
  if (p95Ms >= 20_000) return "abnormal";
  if (p95Ms >= 15_000) return "attention";
  return "normal";
}

export function getCostStatus(totalCostYuan: number, range: TimeRange): MetricStatus {
  const hours = timeRangeToWindowHours(range);
  const dailyCostPace = hours > 0 ? (totalCostYuan * 24) / hours : totalCostYuan;

  if (dailyCostPace >= 20) return "critical";
  if (dailyCostPace >= 10) return "abnormal";
  if (dailyCostPace >= 5) return "attention";
  return "normal";
}

export function getCacheSavingsStatus(savingsPct: number): MetricStatus {
  if (savingsPct < 20) return "critical";
  if (savingsPct < 35) return "abnormal";
  if (savingsPct < 50) return "attention";
  return "normal";
}

export function statusToAccent(status: MetricStatus): "default" | "danger" | "success" | "warning" {
  if (status === "critical" || status === "abnormal") return "danger";
  if (status === "attention") return "warning";
  return "default";
}
