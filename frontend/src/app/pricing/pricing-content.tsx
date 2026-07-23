"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { openBillingCheckout, isUnauthenticatedCheckoutError } from "@/lib/billing";
import { ADD_ONS, PLANS, TRIAL_CREDITS, TRIAL_DAYS, formatPrice, type BillingPeriod, type PlanKey } from "@/lib/pricing";

const PLAN_FEATURES: Record<string, string[]> = {
  free: [
    "300 credits / month",
    "1 product group",
    "Up to 500 reviews per upload",
    "Top issues & highlights",
    "7-day insight history",
    "Community support",
  ],
  starter: [
    "5,000 credits / month",
    "3 product groups",
    "Up to 1,000 reviews per upload",
    "Pain point discovery",
    "Listing optimization cues",
    "Ask Reviews AI Q&A",
    "Translation (batch)",
    "Email support",
  ],
  pro: [
    "15,000 credits / month",
    "Unlimited product groups",
    "Up to 5,000 reviews per upload",
    "All Starter features",
    "Competitor opportunity analysis",
    "Action center & follow-up",
    "Webhook team notifications",
    "Priority support",
  ],
  team: [
    "45,000 credits / month",
    "Everything in Pro",
    "Multi-member collaboration",
    "Role-based permissions",
    "Team notification workflows",
    "Custom analysis templates",
    "API access (10 keys)",
    "SLA guarantee",
    "Dedicated success manager",
  ],
};

const CHECK_ICON = (
  <svg
    className="mt-0.5 h-4 w-4 shrink-0 text-[#4fb99f]"
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
  const [error, setError] = useState<string>("");
  const router = useRouter();
  const checkoutRef = useRef<HTMLDivElement | null>(null);

  async function handlePaidPlanClick(planKey: PlanKey) {
    setError("");
    setCheckoutLoading(planKey);
    try {
      const result = await openBillingCheckout(checkoutRef.current, planKey, period);
      if (!result.configured) {
        setError("Payment not enabled yet. Please contact hello@clueai.co.");
        return;
      }
      if (!result.hasHtml) {
        setError("You already have an active subscription. Manage from Settings.");
        return;
      }
    } catch (err) {
      if (isUnauthenticatedCheckoutError(err)) {
        router.push(`/register?plan=${planKey}&period=${period}`);
        return;
      }
      setError((err as { message?: string }).message || "Operation failed, please try again.");
      console.error("[billing] checkout failed", err);
    } finally {
      setCheckoutLoading(null);
    }
  }

  return (
    <div className="page-bg-warm relative overflow-hidden">
      {/* Floating blobs */}
      <div className="blob-rose pointer-events-none absolute -top-32 -left-32 z-0" />
      <div className="blob-lavender pointer-events-none absolute top-32 -right-24 z-0" />
      <div ref={checkoutRef} className="hidden" aria-hidden="true" />
      {/* Header */}
      <div className="relative z-10 mx-auto max-w-7xl px-6 pb-10 pt-20 text-center lg:px-10">
        {/* Section label pill */}
        <div className="mb-6 flex justify-center">
          <span className="glass-rose inline-flex rounded-pill px-4 py-1.5 text-[13px] font-medium uppercase tracking-[0.05em] text-[#f36f8f]">
            Pricing
          </span>
        </div>
        <h1 className="font-heading text-4xl font-extrabold tracking-normal text-ink md:text-[44px]">
          Pricing for review-driven growth.
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-base text-soft">
          Start with {TRIAL_CREDITS.toLocaleString()} free credits for {TRIAL_DAYS} days. Import reviews, find growth signals, and decide what your team should do next.
        </p>

        {/* Monthly / Annual toggle */}
        <div className="mt-8 inline-flex items-center gap-1 rounded-full border border-[rgba(255,255,255,0.8)] bg-white/60 p-1 backdrop-blur">
          <button
            onClick={() => setPeriod("monthly")}
            className={[
              "rounded-full px-5 py-2 text-sm font-semibold transition-all",
              period === "monthly" ? "bg-[#f36f8f] text-white shadow-[0_4px_12px_rgba(243,111,143,0.3)]" : "text-soft hover:text-ink",
            ].join(" ")}
          >
            Monthly
          </button>
          <button
            onClick={() => setPeriod("annual")}
            className={[
              "flex items-center gap-1.5 rounded-full px-5 py-2 text-sm font-semibold transition-all",
              period === "annual" ? "bg-[#f36f8f] text-white shadow-[0_4px_12px_rgba(243,111,143,0.3)]" : "text-soft hover:text-ink",
            ].join(" ")}
          >
            Annual
            <span
              className={[
                "rounded-full px-1.5 py-0.5 text-[10px] font-bold",
                period === "annual" ? "bg-white/20 text-white" : "bg-[#4fb99f]/15 text-[#4fb99f]",
              ].join(" ")}
            >
              −20%
            </span>
          </button>
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-600" role="alert">{error}</p>
        )}
      </div>

      {/* Plan cards */}
      <div className="relative z-10 mx-auto grid w-full max-w-7xl gap-5 px-6 pb-16 sm:grid-cols-2 lg:grid-cols-4 lg:px-10">
        {(["free", "starter", "pro", "team"] as const).map((key) => {
          const plan = PLANS[key];
          const isPro = key === "pro";
          const isFree = key === "free";
          const price = formatPrice(plan, period);
          const perMonth = period === "annual" && plan.monthlyUsd > 0 ? "/mo, billed annually" : plan.monthlyUsd > 0 ? "/month" : "";

          return (
            <article
              key={key}
              className={[
                "relative flex flex-col rounded-[24px] p-6 transition-all duration-300 hover:-translate-y-1",
                isPro
                  ? "glass-white border-2 border-[#f36f8f] shadow-[0_0_32px_rgba(243,111,143,0.2)]"
                  : "glass-white",
              ].join(" ")}
            >
              {isPro && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-pill bg-[#f36f8f] px-4 py-1 text-xs font-bold tracking-wider text-white shadow-[0_4px_12px_rgba(243,111,143,0.35)]">
                  Most popular ⭐
                </div>
              )}

              <div className="text-sm font-semibold uppercase tracking-[0.08em] text-soft">
                {plan.name}
              </div>

              <div className="mt-3 flex items-baseline gap-1.5">
                <span className={`font-heading text-4xl font-extrabold tracking-normal ${isFree ? "text-[#4fb99f]" : "text-ink"}`}>
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
                    "mt-5 inline-flex min-h-11 w-full items-center justify-center rounded-[12px] px-6 py-3 text-sm font-semibold transition-all hover:scale-[1.02] active:scale-[0.98]",
                    isPro
                      ? "bg-[#f36f8f] text-white shadow-[0_8px_24px_rgba(243,111,143,0.35)] hover:shadow-[0_12px_28px_rgba(243,111,143,0.45)]"
                      : "border border-[rgba(255,255,255,0.8)] bg-white/60 text-ink hover:border-[#f36f8f]/30 hover:text-[#f36f8f]",
                  ].join(" ")}
                >
                  {key === "free" ? "Start free analysis" : "Talk to sales"}
                </Link>
              ) : (
                <button
                  type="button"
                  onClick={() => handlePaidPlanClick(key)}
                  disabled={checkoutLoading !== null}
                  className={[
                    "mt-5 inline-flex min-h-11 w-full items-center justify-center rounded-[12px] px-6 py-3 text-sm font-semibold transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60",
                    isPro
                      ? "bg-[#f36f8f] text-white shadow-[0_8px_24px_rgba(243,111,143,0.35)] hover:shadow-[0_12px_28px_rgba(243,111,143,0.45)]"
                      : "border border-[rgba(255,255,255,0.8)] bg-white/60 text-ink hover:border-[#f36f8f]/30 hover:text-[#f36f8f]",
                  ].join(" ")}
                >
                  {checkoutLoading === key ? "Loading…" : key === "pro" ? "Start Pro workflow" : `Start ${plan.name}`}
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
      <div className="relative z-10 mx-auto max-w-7xl px-6 pb-16 lg:px-10">
        <div className="glass-white p-8">
          <h2 className="font-heading text-2xl font-bold tracking-normal text-ink">
            Need more review capacity?
          </h2>
          <p className="mt-2 text-sm text-soft">
            Add credits when a launch, competitor check, or review monitoring cycle needs more analysis volume.
          </p>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {ADD_ONS.map((addon) => (
              <div
                key={addon.credits}
                className="flex items-center justify-between rounded-[16px] border border-[rgba(255,255,255,0.8)] bg-white/50 p-4 transition-all hover:-translate-y-0.5 hover:shadow-md"
              >
                <div>
                  <div className="font-semibold text-ink">
                    +{addon.credits.toLocaleString()} credits
                  </div>
                  <div className="text-xs text-soft">
                    ${(addon.priceUsd / addon.credits * 1000).toFixed(1)} per 1K credits
                  </div>
                </div>
                <div className="font-heading text-xl font-extrabold text-ink">${addon.priceUsd}</div>
              </div>
            ))}
          </div>

          <p className="mt-4 text-xs text-soft">
            Higher plans are more efficient for recurring monitoring. Pro gives 15K monthly credits plus comparison, action follow-up, and webhook notifications.
          </p>
        </div>
      </div>

      {/* Enterprise row */}
      <div className="relative z-10 mx-auto max-w-7xl px-6 pb-20 lg:px-10">
        <div className="glass-white flex flex-col items-center justify-between gap-4 p-8 sm:flex-row">
          <div>
            <h3 className="font-heading text-xl font-bold text-ink">Enterprise</h3>
            <p className="mt-1 text-sm text-soft">
              200K+ credits/month · Custom integrations · Team notification workflows · SLA
            </p>
          </div>
          <a
            href="mailto:hello@clueai.co"
            className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-[12px] border border-[#f36f8f] bg-white/60 px-6 py-3 text-sm font-semibold text-[#f36f8f] transition-all hover:scale-[1.02] hover:bg-white/80 active:scale-[0.98]"
          >
            Contact us
          </a>
        </div>
      </div>
    </div>
  );
}
