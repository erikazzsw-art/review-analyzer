"use client";

import { useRouter } from "next/navigation";
import { Fragment, useRef, useState } from "react";
import { Check, Minus } from "lucide-react";
import { useTranslations } from "next-intl";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { openBillingCheckout, isUnauthenticatedCheckoutError } from "@/lib/billing";
import {
  PLANS,
  type BillingPeriod,
  type PlanKey,
  type PlanPricing,
} from "@/lib/pricing";

type UpgradePricingDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentPlan: PlanKey;
  onOpenLedger: () => void;
};

const PLAN_ORDER: PlanKey[] = ["free", "starter", "pro", "team"];

/** Maps plan key to highlight translation key suffixes */
const HIGHLIGHT_SUFFIXES: Record<PlanKey, string[]> = {
  free: ["Free0", "Free1", "Free2", "Free3", "Free4"],
  starter: ["Starter0", "Starter1", "Starter2", "Starter3", "Starter4", "Starter5"],
  pro: ["Pro0", "Pro1", "Pro2", "Pro3", "Pro4", "Pro5"],
  team: ["Team0", "Team1", "Team2", "Team3", "Team4", "Team5"],
};

type CellValue = string | boolean;

type ComparisonRow = {
  labelKey: string;
  values: Record<PlanKey, CellValue>;
};

type ComparisonGroup = {
  titleKey: string;
  rows: ComparisonRow[];
};

const COMPARISON_GROUPS: ComparisonGroup[] = [
  {
    titleKey: "creditsQuota",
    rows: [
      { labelKey: "monthlyCredits", values: { free: "300", starter: "5,000", pro: "15,000", team: "45,000" } },
      { labelKey: "uploadLimit", values: { free: "reviews500", starter: "reviews1000", pro: "reviews5000", team: "reviews5000" } },
      { labelKey: "asinAutoFetch", values: { free: "fetch1", starter: "fetch10", pro: "fetch10", team: "fetch50" } },
    ],
  },
  {
    titleKey: "reviewAnalysis",
    rows: [
      { labelKey: "sentimentTagging", values: { free: true, starter: true, pro: true, team: true } },
      { labelKey: "askReviews", values: { free: true, starter: true, pro: true, team: true } },
      { labelKey: "insightReport", values: { free: true, starter: true, pro: true, team: true } },
      { labelKey: "multiProductCompare", values: { free: "compare2", starter: "unlimited", pro: "unlimited", team: "unlimited" } },
    ],
  },
  {
    titleKey: "contentGeneration",
    rows: [
      { labelKey: "adCopy", values: { free: true, starter: true, pro: true, team: true } },
      { labelKey: "translation", values: { free: "trans20", starter: "trans200", pro: "trans200", team: "trans500" } },
    ],
  },
  {
    titleKey: "exportIntegration",
    rows: [
      { labelKey: "excelExport", values: { free: "export10", starter: "unlimited", pro: "unlimited", team: "unlimited" } },
      { labelKey: "webhookIntegration", values: { free: "webhook3", starter: "unlimited", pro: "unlimited", team: "unlimited" } },
      { labelKey: "alertRules", values: { free: "alert3", starter: "unlimited", pro: "unlimited", team: "unlimited" } },
      { labelKey: "apiKeys", values: { free: false, starter: false, pro: "apiComing3", team: "apiComing10" } },
    ],
  },
  {
    titleKey: "teamSupport",
    rows: [
      { labelKey: "multiMember", values: { free: false, starter: false, pro: false, team: true } },
      { labelKey: "rolePermissions", values: { free: false, starter: false, pro: false, team: true } },
      { labelKey: "customerSupport", values: { free: "community", starter: "email", pro: "priority", team: "dedicated" } },
    ],
  },
];

function priceLabel(plan: PlanPricing, period: BillingPeriod): string {
  if (plan.monthlyUsd === 0) return "$0";
  const value = period === "annual" ? plan.annualMonthlyUsd : plan.monthlyUsd;
  return `$${value % 1 === 0 ? value : value.toFixed(1)}`;
}

export function UpgradePricingDialog({
  open,
  onOpenChange,
  currentPlan,
  onOpenLedger,
}: UpgradePricingDialogProps) {
  const t = useTranslations("credit.upgrade");
  const [billingCycle, setBillingCycle] = useState<BillingPeriod>("monthly");
  const [checkoutLoading, setCheckoutLoading] = useState<PlanKey | null>(null);
  const [error, setError] = useState<string>("");
  const checkoutRef = useRef<HTMLDivElement | null>(null);
  const router = useRouter();

  function resolveComparisonValue(planKey: PlanKey, value: CellValue): React.ReactNode {
    if (value === true) {
      return <Check size={14} className="mx-auto text-[#4a7dc7]" strokeWidth={2.5} />;
    }
    if (value === false) {
      return <Minus size={14} className="mx-auto text-soft/60" strokeWidth={2} />;
    }
    if (typeof value === "string") {
      // Pure numeric/format values (start with digit) display as-is
      if (/^\d/.test(value)) return <span>{value}</span>;
      return <span>{t(`comparisonValue.${value}` as Parameters<typeof t>[0])}</span>;
    }
    return <span>{String(value)}</span>;
  }

  async function handlePaidCheckout(planKey: PlanKey) {
    setError("");
    setCheckoutLoading(planKey);
    try {
      const result = await openBillingCheckout(checkoutRef.current);
      if (!result.hasHtml) {
        onOpenChange(false);
        return;
      }
    } catch (err) {
      if (isUnauthenticatedCheckoutError(err)) {
        onOpenChange(false);
        router.push(`/register?plan=${planKey}`);
        return;
      }
      setError((err as { message?: string }).message || "Operation failed, please try again");
    } finally {
      setCheckoutLoading(null);
    }
  }

  const isPaidCurrent = currentPlan !== "free";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-4xl gap-0 overflow-hidden rounded-shell border-line bg-white p-0 shadow-card">
        <DialogHeader className="space-y-3 border-b border-line px-6 pb-4 pt-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <DialogTitle className="font-heading text-xl font-extrabold tracking-[-0.03em] text-ink">
              {t("title")}
            </DialogTitle>
            <div className="inline-flex items-center gap-1 rounded-full border border-line bg-white p-1 shadow-sm">
              <button
                type="button"
                onClick={() => setBillingCycle("monthly")}
                className={[
                  "rounded-full px-3 py-1 text-xs font-semibold transition",
                  billingCycle === "monthly"
                    ? "bg-ink text-white"
                    : "text-soft hover:text-ink",
                ].join(" ")}
              >
                {t("monthly")}
              </button>
              <button
                type="button"
                onClick={() => setBillingCycle("annual")}
                className={[
                  "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition",
                  billingCycle === "annual"
                    ? "bg-ink text-white"
                    : "text-soft hover:text-ink",
                ].join(" ")}
              >
                {t("annual")}
                <span
                  className={[
                    "rounded-full px-1.5 py-0.5 text-[10px] font-bold",
                    billingCycle === "annual"
                      ? "bg-[#d94d72] text-white"
                      : "bg-emerald-100 text-emerald-700",
                  ].join(" ")}
                >
                  {t("annualDiscount")}
                </span>
              </button>
            </div>
          </div>
        </DialogHeader>

        <div className="max-h-[calc(90vh-160px)] overflow-y-auto px-6 py-6">
          {/* Plan cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PLAN_ORDER.map((key) => {
              const plan = PLANS[key];
              const isPro = key === "pro";
              const isCurrent = key === currentPlan;
              const price = priceLabel(plan, billingCycle);
              const perLabel =
                plan.monthlyUsd === 0
                  ? ""
                  : billingCycle === "annual"
                  ? t("perMonthAnnual")
                  : t("perMonth");

              let cta: React.ReactNode = null;
              if (isCurrent) {
                cta = (
                  <button
                    type="button"
                    disabled
                    className="mt-4 inline-flex w-full items-center justify-center rounded-pill border border-line bg-line/40 px-4 py-2 text-xs font-semibold text-soft"
                  >
                    {t("currentPlan")}
                  </button>
                );
              } else if (key === "free" && isPaidCurrent) {
                cta = null;
              } else if (key === "team") {
                cta = (
                  <a
                    href="mailto:hello@clueai.co"
                    className="mt-4 inline-flex w-full items-center justify-center rounded-pill border border-line bg-white px-4 py-2 text-xs font-semibold text-ink shadow-sm transition hover:border-ink/20"
                  >
                    {t("contactSales")}
                  </a>
                );
              } else if (!isPaidCurrent || key !== "free") {
                cta = (
                  <button
                    type="button"
                    onClick={() => handlePaidCheckout(key)}
                    disabled={checkoutLoading !== null}
                    className={[
                      "mt-4 inline-flex w-full items-center justify-center rounded-pill px-4 py-2 text-xs font-semibold shadow-card transition disabled:opacity-50",
                      isPro
                        ? "bg-[#d94d72] text-white hover:bg-[#c4405f]"
                        : "border border-line bg-white text-ink hover:border-ink/20",
                    ].join(" ")}
                  >
                    {checkoutLoading === key
                      ? t("loading")
                      : isPaidCurrent
                      ? t("upgradePlan")
                      : t("upgradeNow")}
                  </button>
                );
              }

              return (
                <article
                  key={key}
                  className={[
                    "relative flex flex-col rounded-shell border p-5 shadow-card",
                    isPro
                      ? "border-2 border-[#d94d72] bg-white"
                      : "border-line bg-white/86",
                  ].join(" ")}
                >
                  {isPro && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-pill bg-[#d94d72] px-3 py-0.5 text-[10px] font-bold tracking-wider text-white">
                      {t("mostPopular")}
                    </div>
                  )}

                  <div className="text-xs font-semibold uppercase tracking-[0.14em] text-soft">
                    {t(`planName.${key}` as Parameters<typeof t>[0])}
                  </div>

                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
                      {price}
                    </span>
                    {perLabel && (
                      <span className="text-[11px] font-medium text-soft">
                        {perLabel}
                      </span>
                    )}
                  </div>

                  <div className="mt-1 text-xs text-soft">
                    {plan.credits.toLocaleString()} {t("creditsPerMonth")}
                  </div>

                  {billingCycle === "annual" && plan.annualTotalUsd > 0 && (
                    <div className="mt-0.5 text-[11px] text-soft">
                      {t("annualTotal", { total: plan.annualTotalUsd })}
                    </div>
                  )}

                  {cta}

                  <ul className="mt-4 space-y-1.5 border-t border-line pt-4">
                    {HIGHLIGHT_SUFFIXES[key].map((suffix) => (
                      <li
                        key={suffix}
                        className="flex items-start gap-1.5 text-xs leading-5 text-ink"
                      >
                        <Check
                          size={13}
                          className="mt-0.5 shrink-0 text-[#4a7dc7]"
                          strokeWidth={2.5}
                        />
                        <span>{t(`planHighlight${suffix}` as Parameters<typeof t>[0])}</span>
                      </li>
                    ))}
                  </ul>
                </article>
              );
            })}
          </div>

          {/* Feature comparison table */}
          <div className="mt-8 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-0 text-sm">
              <thead>
                <tr>
                  <th
                    scope="col"
                    className="sticky left-0 z-10 min-w-[160px] border-b border-line bg-white px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-soft"
                  >
                    {t("comparisonTitle")}
                  </th>
                  {PLAN_ORDER.map((planKey) => (
                    <th
                      key={planKey}
                      scope="col"
                      className={[
                        "border-b border-line px-4 py-3 text-center text-xs font-semibold",
                        planKey === "pro" ? "text-[#d94d72]" : "text-ink",
                      ].join(" ")}
                    >
                      {t(`planName.${planKey}` as Parameters<typeof t>[0])}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {COMPARISON_GROUPS.map((group) => (
                  <Fragment key={group.titleKey}>
                    <tr>
                      <th
                        scope="colgroup"
                        colSpan={5}
                        className="sticky left-0 bg-hero-wash px-4 py-2 text-left text-xs font-semibold text-soft"
                      >
                        {t(`comparisonGroup.${group.titleKey}` as Parameters<typeof t>[0])}
                      </th>
                    </tr>
                    {group.rows.map((row) => (
                      <tr key={row.labelKey} className="border-t border-line">
                        <th
                          scope="row"
                          className="sticky left-0 z-10 bg-white px-4 py-2.5 text-left text-xs font-medium text-ink"
                        >
                          {t(`comparisonRow.${row.labelKey}` as Parameters<typeof t>[0])}
                        </th>
                        {PLAN_ORDER.map((planKey) => {
                          const value = row.values[planKey];
                          return (
                            <td
                              key={planKey}
                              className="px-4 py-2.5 text-center text-xs text-ink tabular-nums"
                            >
                              {resolveComparisonValue(planKey, value)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <div className="flex flex-col gap-2 border-t border-line bg-[#f8f6f3] px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          {error ? (
            <p className="text-xs text-red-600">{error}</p>
          ) : (
            <span className="text-xs text-soft">
              {t("footerHint")}
            </span>
          )}
          <button
            type="button"
            onClick={onOpenLedger}
            className="text-xs font-semibold text-rose hover:underline"
          >
            {t("viewLedger")}
          </button>
        </div>

        <div ref={checkoutRef} className="hidden" aria-hidden="true" />
      </DialogContent>
    </Dialog>
  );
}
