"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import type { QuotaItem } from "@/lib/api/server";
import {
  DIMENSION_LABEL_KEY,
  PERIOD_LABEL_KEY,
  PLAN_LABEL_KEY,
} from "@/components/quota/quota-groups";

type QuotaPanelProps = {
  items: QuotaItem[];
};

export function QuotaPanel({ items }: QuotaPanelProps) {
  const t = useTranslations("quotaDialog");
  const tPanel = useTranslations("quotaPanel");
  const plan = items[0]?.plan || "free";
  const usableItems = items.filter((item) => !item.error && item.period !== "per_request");
  const planLabel = t(PLAN_LABEL_KEY[plan] ?? "plans.free");

  return (
    <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            {tPanel("badge")}
          </div>
          <h3 className="mt-3 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            {tPanel("currentPlanPrefix")}{planLabel}
          </h3>
        </div>
        {plan === "free" && (
          <Link
            href="/pricing"
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-[#d94d72] px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:bg-[#c4405f]"
          >
            {tPanel("upgrade")}
          </Link>
        )}
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {usableItems.map((item) => {
          const labelKey = DIMENSION_LABEL_KEY[item.dimension];
          const label = labelKey ? t(labelKey) : item.dimension;
          const periodKey = PERIOD_LABEL_KEY[item.period];
          const period = periodKey ? t(periodKey) : item.period;
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
                <div className="mt-3 text-sm text-soft">{t("unlimited")}</div>
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
                    {tPanel("remaining")} {item.remaining ?? item.limit - (item.used ?? 0)} {item.unit || ""}
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
