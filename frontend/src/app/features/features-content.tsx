"use client";

import { FeatureCarousel } from "@/components/marketing/feature-carousel";
import { useTranslations } from "next-intl";

export function FeaturesContent() {
  const t = useTranslations("features");

  return (
    <main className="relative overflow-hidden">
      {/* Decorative blobs */}
      <div className="pointer-events-none absolute -top-32 left-1/2 h-[500px] w-[500px] -translate-x-1/2 rounded-full bg-rose/10 blur-[120px]" />
      <div className="pointer-events-none absolute top-1/3 -right-40 h-[400px] w-[400px] rounded-full bg-lavender/8 blur-[140px]" />

      {/* Section label */}
      <div className="pt-20 pb-4 text-center">
        <span className="inline-block rounded-full border border-rose/20 bg-rose/10 px-4 py-1.5 font-body text-[13px] font-medium uppercase tracking-[0.12em] text-rose backdrop-blur">
          {t("label")}
        </span>
      </div>

      {/* Title */}
      <h1 className="px-4 text-center font-heading text-[44px] font-extrabold leading-[1.15] tracking-[-0.02em] text-ink">
        {t("title")}
      </h1>

      {/* Carousel */}
      <div className="mt-12 pb-6">
        <FeatureCarousel />
      </div>
    </main>
  );
}
