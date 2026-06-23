import Link from "next/link";

import type { QuotaItem } from "@/lib/api/server";

const dimensionLabels: Record<string, string> = {
  review_analyze: "评论分析",
  ask_review: "问评论 (RAG)",
  ad_copy: "文案生成",
  excel_export: "Excel 导出",
  compare_products: "对比产品数",
  webhook_count: "Webhook 数",
  global_rules: "推送规则",
};

const periodLabels: Record<string, string> = {
  monthly: "每月",
  daily: "每日",
  forever: "累计",
  concurrent: "同时",
  per_request: "单次",
};

const planLabels: Record<string, string> = {
  free: "Free",
  pro_early: "Pro (早鸟)",
  pro: "Pro",
  team: "Team",
};

type QuotaPanelProps = {
  items: QuotaItem[];
};

export function QuotaPanel({ items }: QuotaPanelProps) {
  const plan = items[0]?.plan || "free";
  const usableItems = items.filter((item) => !item.error && item.period !== "per_request");

  return (
    <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            用量看板
          </div>
          <h3 className="mt-3 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            当前套餐：{planLabels[plan] || plan}
          </h3>
        </div>
        {plan === "free" && (
          <Link
            href="/pricing"
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-[#d94d72] px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:bg-[#c4405f]"
          >
            升级 Pro
          </Link>
        )}
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {usableItems.map((item) => {
          const label = dimensionLabels[item.dimension] || item.dimension;
          const period = periodLabels[item.period] || item.period;
          const pct =
            item.unlimited || !item.limit || item.limit === -1
              ? 0
              : Math.min(((item.used ?? 0) / item.limit) * 100, 100);
          const isHigh = pct >= 80;

          return (
            <div
              key={item.dimension}
              className="rounded-card border border-line bg-white px-4 py-4"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-ink">{label}</span>
                <span className="text-xs text-soft">{period}</span>
              </div>

              {item.unlimited || item.limit === -1 ? (
                <div className="mt-3 text-sm text-soft">无限制</div>
              ) : (
                <>
                  <div className="mt-3 flex items-baseline gap-1">
                    <span className={["text-lg font-bold", isHigh ? "text-[#d94d72]" : "text-ink"].join(" ")}>
                      {item.used ?? 0}
                    </span>
                    <span className="text-sm text-soft">
                      / {item.limit} {item.unit || ""}
                    </span>
                  </div>
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#f0f0f0]">
                    <div
                      className={[
                        "h-full rounded-full transition-all",
                        isHigh ? "bg-[#d94d72]" : "bg-[#4a7dc7]",
                      ].join(" ")}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="mt-1.5 text-xs text-soft">
                    剩余 {item.remaining ?? item.limit - (item.used ?? 0)} {item.unit || ""}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
