"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { openBillingCheckout, isUnauthenticatedCheckoutError } from "@/lib/billing";
import { ADD_ONS, PLANS, TRIAL_CREDITS, TRIAL_DAYS, formatPrice, type BillingPeriod } from "@/lib/pricing";

const PLAN_FEATURES: Record<string, string[]> = {
  free: [
    "300 credits / month",
    "1 product group",
    "Up to 500 reviews per upload",
    "Sentiment analysis + tagging",
    "7-day analysis history",
    "Community support",
  ],
  starter: [
    "5,000 credits / month",
    "3 product groups",
    "Up to 1,000 reviews per upload",
    "Ask Reviews AI Q&A",
    "Ad copy generation",
    "Translation (batch)",
    "Email support",
  ],
  pro: [
    "15,000 credits / month",
    "Unlimited product groups",
    "Up to 5,000 reviews per upload",
    "All Starter features",
    "Multi-product comparison",
    "Action center + tracking",
    "Webhook integration",
    "Priority support",
  ],
  team: [
    "45,000 credits / month",
    "Everything in Pro",
    "Multi-member collaboration",
    "Role-based permissions",
    "Custom analysis templates",
    "API access (10 keys)",
    "SLA guarantee",
    "Dedicated success manager",
  ],
};

const CHECK_ICON = (
  <svg
    className="mt-0.5 h-4 w-4 shrink-0 text-[#4a7dc7]"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    strokeWidth={2.5}
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
  </svg>
);

export default function PricingContent() {
  const [period, setPeriod] = useState<BillingPeriod>("monthly");
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const router = useRouter();
  const checkoutRef = useRef<HTMLDivElement | null>(null);

  async function handlePaidPlanClick(planKey: "starter" | "pro") {
    setCheckoutLoading(planKey);
    try {
      await openBillingCheckout(checkoutRef.current);
    } catch (err) {
      if (isUnauthenticatedCheckoutError(err)) {
        router.push(`/register?plan=${planKey}`);
        return;
      }
      router.push(`/register?plan=${planKey}`);
    } finally {
      setCheckoutLoading(null);
    }
  }

  return (
    <div className="bg-hero-wash">
      <div ref={checkoutRef} className="hidden" aria-hidden="true" />
      {/* Header */}
      <div className="mx-auto max-w-7xl px-6 pb-10 pt-20 text-center lg:px-10">
        <p className="text-sm font-semibold uppercase tracking-[0.12em] text-[#4a7dc7]">
          Pricing
        </p>
        <h1 className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.03em] text-ink lg:text-5xl">
          Simple, transparent pricing.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base text-soft">
          Start with {TRIAL_CREDITS.toLocaleString()} free credits — {TRIAL_DAYS} days, no credit card required.
        </p>

        {/* Monthly / Annual toggle */}
        <div className="mt-8 inline-flex items-center gap-1 rounded-full border border-line bg-white p-1 shadow-card">
          <button
            onClick={() => setPeriod("monthly")}
            className={[
              "rounded-full px-4 py-1.5 text-sm font-semibold transition",
              period === "monthly" ? "bg-ink text-white" : "text-soft hover:text-ink",
            ].join(" ")}
          >
            Monthly
          </button>
          <button
            onClick={() => setPeriod("annual")}
            className={[
              "flex items-center gap-1.5 rounded-full px-4 py-1.5 text-sm font-semibold transition",
              period === "annual" ? "bg-ink text-white" : "text-soft hover:text-ink",
            ].join(" ")}
          >
            Annual
            <span
              className={[
                "rounded-full px-1.5 py-0.5 text-[10px] font-bold",
                period === "annual" ? "bg-[#d94d72] text-white" : "bg-emerald-100 text-emerald-700",
              ].join(" ")}
            >
              −20%
            </span>
          </button>
        </div>
      </div>

      {/* Plan cards */}
      <div className="mx-auto grid w-full max-w-7xl gap-5 px-6 pb-16 sm:grid-cols-2 lg:grid-cols-4 lg:px-10">
        {(["free", "starter", "pro", "team"] as const).map((key) => {
          const plan = PLANS[key];
          const isPro = key === "pro";
          const price = formatPrice(plan, period);
          const perMonth = period === "annual" && plan.monthlyUsd > 0 ? "/mo, billed annually" : plan.monthlyUsd > 0 ? "/month" : "";

          return (
            <article
              key={key}
              className={[
                "relative flex flex-col rounded-shell border p-6 shadow-card",
                isPro ? "border-2 border-[#d94d72] bg-white" : "border-line bg-white/86",
              ].join(" ")}
            >
              {isPro && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-pill bg-[#d94d72] px-4 py-1 text-xs font-bold tracking-wider text-white">
                  Most popular ⭐
                </div>
              )}

              <div className="text-sm font-semibold uppercase tracking-[0.12em] text-soft">
                {plan.name}
              </div>

              <div className="mt-3 flex items-baseline gap-1.5">
                <span className="font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
                  {price}
                </span>
                {perMonth && (
                  <span className="text-xs font-medium text-soft">{perMonth}</span>
                )}
              </div>

              <div className="mt-1 text-sm text-soft">
                {plan.credits.toLocaleString()} credits / month
              </div>

              {period === "annual" && plan.annualTotalUsd > 0 && (
                <div className="mt-0.5 text-xs text-soft">
                  ${plan.annualTotalUsd} billed annually
                </div>
              )}

              {key === "free" || key === "team" ? (
                <Link
                  href={key === "free" ? "/register" : `/register?plan=${key}`}
                  className={[
                    "mt-5 inline-flex min-h-10 w-full items-center justify-center rounded-pill px-4 py-2.5 text-sm font-semibold shadow-card transition",
                    isPro
                      ? "bg-[#d94d72] text-white hover:bg-[#c4405f]"
                      : "border border-line bg-white text-ink hover:border-ink/20",
                  ].join(" ")}
                >
                  {key === "free" ? "Get started free" : "Get Team"}
                </Link>
              ) : (
                <button
                  type="button"
                  onClick={() => handlePaidPlanClick(key)}
                  disabled={checkoutLoading !== null}
                  className={[
                    "mt-5 inline-flex min-h-10 w-full items-center justify-center rounded-pill px-4 py-2.5 text-sm font-semibold shadow-card transition disabled:opacity-60",
                    isPro
                      ? "bg-[#d94d72] text-white hover:bg-[#c4405f]"
                      : "border border-line bg-white text-ink hover:border-ink/20",
                  ].join(" ")}
                >
                  {checkoutLoading === key ? "Loading…" : `Get ${plan.name}`}
                </button>
              )}

              <div className="mt-5 space-y-2.5 border-t border-line pt-5">
                {PLAN_FEATURES[key].map((feature) => (
                  <div key={feature} className="flex items-start gap-2 text-sm leading-5 text-ink">
                    {CHECK_ICON}
                    <span>{feature}</span>
                  </div>
                ))}
                {(key === "pro" || key === "team") && (
                  <div className="flex items-start gap-2 text-sm leading-5 text-soft/70">
                    {CHECK_ICON}
                    <span>{key === "pro" ? "3" : "10"} API keys — Coming soon</span>
                  </div>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {/* Add-ons section */}
      <div className="mx-auto max-w-7xl px-6 pb-16 lg:px-10">
        <div className="rounded-shell border border-line bg-white p-8 shadow-card">
          <h2 className="font-heading text-2xl font-bold tracking-[-0.02em] text-ink">
            Need more credits?
          </h2>
          <p className="mt-2 text-sm text-soft">
            Upgrade when you need more. Top-up credits never expire and stack on top of your monthly grant.
          </p>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {ADD_ONS.map((addon) => (
              <div
                key={addon.credits}
                className="flex items-center justify-between rounded-xl border border-line bg-hero-wash p-4"
              >
                <div>
                  <div className="font-semibold text-ink">
                    +{addon.credits.toLocaleString()} credits
                  </div>
                  <div className="text-xs text-soft">
                    ${(addon.priceUsd / addon.credits * 1000).toFixed(1)} per 1K credits
                  </div>
                </div>
                <div className="text-xl font-extrabold text-ink">${addon.priceUsd}</div>
              </div>
            ))}
          </div>

          <p className="mt-4 text-xs text-soft">
            Upgrading to a higher plan is always cheaper than stacking add-ons. Pro $29/mo gives 15K credits vs. Starter + $18 add-on = 15K credits at $30.
          </p>
        </div>
      </div>

      {/* Enterprise row */}
      <div className="mx-auto max-w-7xl px-6 pb-20 lg:px-10">
        <div className="flex flex-col items-center justify-between gap-4 rounded-shell border border-line bg-white p-8 shadow-card sm:flex-row">
          <div>
            <h3 className="font-heading text-xl font-bold text-ink">Enterprise</h3>
            <p className="mt-1 text-sm text-soft">
              200K+ credits/month · Custom integrations · Dedicated support · SLA
            </p>
          </div>
          <a
            href="mailto:hello@clueai.co"
            className="inline-flex min-h-10 shrink-0 items-center gap-2 rounded-pill border border-line bg-white px-5 py-2.5 text-sm font-semibold text-ink shadow-card transition hover:border-ink/20"
          >
            Contact us
          </a>
        </div>
      </div>
    </div>
  );
}
