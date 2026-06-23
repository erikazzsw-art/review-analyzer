export type QuotaGroup = {
  key: string;
  titleKey: string;
  dimensions: string[];
};

export const QUOTA_GROUPS: QuotaGroup[] = [
  {
    key: "reviewAnalysis",
    titleKey: "groups.reviewAnalysis",
    dimensions: ["review_analyze", "ask_review", "upload_rows_per_file", "asin_fetch"],
  },
  {
    key: "adCopy",
    titleKey: "groups.adCopy",
    dimensions: ["ad_copy"],
  },
  {
    key: "exportCompare",
    titleKey: "groups.exportCompare",
    dimensions: ["excel_export", "compare_products"],
  },
  {
    key: "pushAlert",
    titleKey: "groups.pushAlert",
    dimensions: ["webhook_count", "global_rules", "product_rules"],
  },
];

export const DIMENSION_LABEL_KEY: Record<string, string> = {
  review_analyze: "dimensions.review_analyze.label",
  ask_review: "dimensions.ask_review.label",
  ad_copy: "dimensions.ad_copy.label",
  excel_export: "dimensions.excel_export.label",
  compare_products: "dimensions.compare_products.label",
  webhook_count: "dimensions.webhook_count.label",
  global_rules: "dimensions.global_rules.label",
  product_rules: "dimensions.product_rules.label",
  upload_rows_per_file: "dimensions.upload_rows_per_file.label",
  asin_fetch: "dimensions.asin_fetch.label",
};

export const DIMENSION_HINT_KEY: Record<string, string> = {
  review_analyze: "dimensions.review_analyze.hint",
  ask_review: "dimensions.ask_review.hint",
  ad_copy: "dimensions.ad_copy.hint",
  excel_export: "dimensions.excel_export.hint",
  compare_products: "dimensions.compare_products.hint",
  webhook_count: "dimensions.webhook_count.hint",
  global_rules: "dimensions.global_rules.hint",
  product_rules: "dimensions.product_rules.hint",
  upload_rows_per_file: "dimensions.upload_rows_per_file.hint",
  asin_fetch: "dimensions.asin_fetch.hint",
};

export const PERIOD_LABEL_KEY: Record<string, string> = {
  monthly: "periods.monthly",
  daily: "periods.daily",
  forever: "periods.forever",
  concurrent: "periods.concurrent",
  per_request: "periods.per_request",
};

export const PLAN_LABEL_KEY: Record<string, string> = {
  free: "plans.free",
  pro_early: "plans.pro_early",
  pro: "plans.pro",
  team: "plans.team",
};

export function nextResetDate(): string {
  const now = new Date();
  const next = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  const y = next.getFullYear();
  const m = String(next.getMonth() + 1).padStart(2, "0");
  const d = String(next.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}
