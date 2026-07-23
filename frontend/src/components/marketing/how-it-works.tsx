"use client";

import { useTranslations } from "next-intl";
import { Upload, BarChart3, Target, ArrowRight } from "lucide-react";

const STEPS = [
  {
    icon: Upload,
    color: "text-[#f36f8f]",
    bgColor: "bg-[rgba(243,111,143,0.12)]",
    key: "upload",
  },
  {
    icon: BarChart3,
    color: "text-[#8d7be8]",
    bgColor: "bg-[rgba(141,123,232,0.12)]",
    key: "analyze",
  },
  {
    icon: Target,
    color: "text-[#4fb99f]",
    bgColor: "bg-[rgba(79,185,159,0.12)]",
    key: "action",
  },
] as const;

export function HowItWorks() {
  const t = useTranslations("marketing.howItWorks");

  return (
    <section className="mx-auto w-full max-w-7xl px-6 pb-20 lg:px-10">
      {/* Section label */}
      <div className="mb-10 flex justify-center">
        <span className="glass-rose inline-flex rounded-pill px-4 py-1.5 text-[13px] font-medium uppercase tracking-[0.05em] text-[#f36f8f]">
          {t("label")}
        </span>
      </div>

      {/* 3 steps grid */}
      <div className="relative grid gap-6 md:grid-cols-3">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          return (
            <div key={step.key} className="relative flex flex-col items-center text-center">
              {/* Step card */}
              <div className="glass-white w-full px-6 py-8 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_8px_32px_rgba(0,0,0,0.08)]">
                {/* Icon circle */}
                <div
                  className={`mx-auto inline-flex h-14 w-14 items-center justify-center rounded-full ${step.bgColor}`}
                >
                  <Icon className={`h-7 w-7 ${step.color}`} />
                </div>

                {/* Step number */}
                <div className="mt-4 font-heading text-xl font-extrabold tracking-normal text-ink">
                  {t(`step${index + 1}Title`)}
                </div>

                {/* Description */}
                <p className="mt-2 text-sm leading-relaxed text-soft">
                  {t(`step${index + 1}Desc`)}
                </p>
              </div>

              {/* Arrow connector between cards (desktop only) */}
              {index < 2 && (
                <div className="absolute -right-4 top-1/2 z-10 hidden -translate-y-1/2 md:block">
                  <ArrowRight className="h-6 w-6 text-[#d8cfde]" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
