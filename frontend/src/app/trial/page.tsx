import Link from "next/link";
import { Suspense } from "react";
import { useTranslations } from "next-intl";
import { getTranslations } from "next-intl/server";
import { Shield, Zap, TrendingUp } from "lucide-react";

import { TrialForm } from "@/components/marketing/trial-form";
import { buildMarketingMetadata } from "@/lib/seo";

export async function generateMetadata() {
  const t = await getTranslations("trial");
  return buildMarketingMetadata({
    title: t("pageEyebrow"),
    description: t("formSubtitle"),
    path: "/trial",
  });
}

const STEPS = [
  { num: 1, key: "step1" as const, keywordKey: "step1Keyword" as const },
  { num: 2, key: "step2" as const, keywordKey: "step2Keyword" as const },
  { num: 3, key: "step3" as const, keywordKey: "step3Keyword" as const },
];

const BENEFITS = [
  { Icon: Shield, key: "benefitSecure" as const },
  { Icon: Zap, key: "benefitFast" as const },
  { Icon: TrendingUp, key: "benefitGrowth" as const },
];

export default function TrialPage() {
  const t = useTranslations("trial");

  return (
    <div className="flex min-h-screen flex-col page-bg-warm">
      {/* Top nav bar */}
      <header className="sticky top-0 z-50 flex h-16 items-center border-b border-[rgba(0,0,0,0.06)] bg-white/80 backdrop-blur-[20px]">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 lg:px-10">
          {/* Logo */}
          <Link href="/" className="inline-flex items-center gap-2.5">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-xs font-extrabold text-white shadow-sm">
              RL
            </span>
            <span className="font-heading text-lg font-extrabold tracking-[-0.02em] text-ink">
              ReviewLens
            </span>
          </Link>

          {/* Right: login link */}
          <p className="text-sm text-soft">
            {t("hasAccount")}
            <Link
              href="/login"
              className="ml-1 font-semibold text-[#f36f8f] hover:underline"
            >
              {t("goLogin")}
            </Link>
          </p>
        </div>
      </header>

      {/* Two-column body */}
      <div className="flex flex-1 flex-col lg:flex-row">
        {/* === Left 60%: steps + benefits === */}
        <section className="relative flex flex-[3] flex-col items-center justify-center overflow-hidden px-6 py-12 lg:px-16">
          {/* Floating blobs */}
          <div className="blob-rose absolute -top-32 -left-32 z-0" />
          <div className="blob-lavender absolute top-20 -right-24 z-0" />

          <div className="relative z-10 w-full max-w-[540px]">
            {/* Page title */}
            <div className="mb-12 text-center">
              <span className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold uppercase tracking-[0.12em] text-[#d94d72]">
                {t("pageEyebrow")}
              </span>
              <h1 className="mt-5 font-heading text-3xl font-extrabold leading-[1.15] tracking-[-0.03em] text-ink md:text-4xl">
                {t("pageTitle")}
              </h1>
            </div>

            {/* 3 step indicators */}
            <div className="flex items-start justify-between gap-4">
              {STEPS.map((step, i) => (
                <div key={step.num} className="flex flex-1 flex-col items-center text-center">
                  {/* Rose circle number */}
                  <span
                    className="inline-flex h-16 w-16 items-center justify-center rounded-full text-2xl font-extrabold text-white shadow-[0_8px_32px_rgba(243,111,143,0.3)]"
                    style={{ background: "#f36f8f" }}
                  >
                    {step.num}
                  </span>
                  <p className="mt-4 font-heading text-base font-bold tracking-[-0.01em] text-ink">
                    {t(step.key)}
                  </p>
                  <p className="mt-1.5 text-sm leading-relaxed text-soft">
                    {t(step.keywordKey)}
                  </p>

                  {/* Connector line between steps */}
                  {i < STEPS.length - 1 && (
                    <div className="mt-6 hidden h-[2px] w-full bg-[rgba(243,111,143,0.2)] md:block" />
                  )}
                </div>
              ))}
            </div>

            {/* Benefit icons row */}
            <div className="mt-14 flex items-center justify-center gap-10">
              {BENEFITS.map(({ Icon, key }) => (
                <div
                  key={key}
                  className="flex flex-col items-center gap-2 text-soft"
                >
                  <Icon
                    className="h-7 w-7 text-[#f36f8f]/60"
                    strokeWidth={1.5}
                  />
                  <span className="text-xs font-medium tracking-wide text-soft">
                    {t(key)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* === Right 40%: glass card + form === */}
        <section className="flex flex-[2] items-center justify-center px-6 py-12 lg:px-10">
          <div className="w-full max-w-[400px]">
            <div className="glass-white px-7 py-8 md:px-9 md:py-10">
              <Suspense fallback={null}>
                <TrialForm />
              </Suspense>
            </div>

            {/* "No credit card" reassurance below card */}
            <p className="mt-4 text-center text-xs text-soft">
              🔒 {t("formSubtitle")}
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
