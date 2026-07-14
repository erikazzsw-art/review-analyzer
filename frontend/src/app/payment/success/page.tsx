"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle, Sparkles } from "lucide-react";
import { PLANS, MONTHLY_GRANT, type PlanKey } from "@/lib/pricing";

type PlanStatus = "pending" | "activated" | "error";

export default function PaymentSuccessPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const planKey = (searchParams.get("plan") || "starter") as PlanKey;
  const [planStatus, setPlanStatus] = useState<PlanStatus>("pending");
  const plan = PLANS[planKey];

  // Poll the plan status until the webhook updates it
  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 20; // ~40 seconds

    async function checkPlan() {
      try {
        const res = await fetch("/api/billing", { credentials: "include" });
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled) {
          if (data.plan === planKey) {
            setPlanStatus("activated");
          } else if (++attempts >= maxAttempts) {
            setPlanStatus("error");
          } else {
            setTimeout(checkPlan, 2000);
          }
        }
      } catch {
        if (!cancelled && ++attempts >= maxAttempts) {
          setPlanStatus("error");
        } else if (!cancelled) {
          setTimeout(checkPlan, 2000);
        }
      }
    }

    // Start with a 1s delay to let the webhook arrive
    const timer = setTimeout(checkPlan, 1000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [planKey]);

  return (
    <div className="flex min-h-[80vh] flex-col items-center justify-center px-6">
      <div className="mx-auto w-full max-w-md text-center">
        {/* Success icon */}
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
          {planStatus === "activated" ? (
            <Sparkles className="h-8 w-8 text-emerald-600" />
          ) : (
            <CheckCircle className="h-8 w-8 text-emerald-600" />
          )}
        </div>

        {/* Title */}
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">
          {planStatus === "activated"
            ? "Welcome to ClueAI!"
            : "Payment successful!"}
        </h1>

        <p className="mt-3 text-base text-gray-500">
          {planStatus === "activated" ? (
            <>Your <span className="font-semibold text-gray-900">{plan.name}</span> plan is now active.</>
          ) : planStatus === "error" ? (
            "Your plan is being activated. It may take a few more moments."
          ) : (
            <>Your <span className="font-semibold text-gray-900">{plan.name}</span> plan is being activated…</>
          )}
        </p>

        {/* Plan details */}
        <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Plan</span>
            <span className="text-sm font-semibold text-gray-900">{plan.name}</span>
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3">
            <span className="text-sm text-gray-500">Monthly credits</span>
            <span className="text-sm font-semibold text-gray-900">
              {(MONTHLY_GRANT[planKey] || 0).toLocaleString()}
            </span>
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3">
            <span className="text-sm text-gray-500">Price</span>
            <span className="text-sm font-semibold text-gray-900">
              ${plan.monthlyUsd}/month
            </span>
          </div>
        </div>

        {/* Status indicator */}
        {planStatus === "pending" && (
          <div className="mt-6 flex items-center justify-center gap-2 text-sm text-amber-600">
            <span className="inline-block h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
            Activating your plan…
          </div>
        )}
        {planStatus === "error" && (
          <p className="mt-6 text-sm text-gray-500">
            If your plan doesn&apos;t update within a few minutes, please contact{" "}
            <a href="mailto:hello@clueai.co" className="text-blue-600 underline">
              hello@clueai.co
            </a>
          </p>
        )}

        {/* Actions */}
        <div className="mt-8 flex flex-col items-center gap-3">
          <Link
            href="/workspace"
            className="inline-flex min-h-10 items-center justify-center rounded-full bg-gray-900 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-gray-800"
          >
            Go to workspace
          </Link>
          <Link
            href="/settings/push"
            className="text-sm text-gray-500 underline-offset-2 hover:text-gray-700 hover:underline"
          >
            Configure push notifications
          </Link>
        </div>
      </div>
    </div>
  );
}
