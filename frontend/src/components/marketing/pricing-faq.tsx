"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ChevronDown } from "lucide-react";

export function PricingFaq() {
  const t = useTranslations("marketing.pricingFaq");
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const faqs = [
    { q: t("q1"), a: t("a1") },
    { q: t("q2"), a: t("a2") },
    { q: t("q3"), a: t("a3") },
    { q: t("q4"), a: t("a4") },
    { q: t("q5"), a: t("a5") },
    { q: t("q6"), a: t("a6") },
  ];

  return (
    <section className="relative z-10 mx-auto w-full max-w-3xl px-6 pb-20 lg:px-10">
      <h2 className="text-center font-heading text-3xl font-extrabold tracking-[-0.02em] text-ink">
        {t("title")}
      </h2>
      <div className="mt-8 space-y-3">
        {faqs.map((faq, index) => (
          <div
            key={index}
            className={`glass-white transition-all duration-300 ${
              openIndex === index
                ? "shadow-[0_0_24px_rgba(243,111,143,0.08)]"
                : ""
            }`}
          >
            <button
              type="button"
              onClick={() => setOpenIndex(openIndex === index ? null : index)}
              className={`flex w-full items-center justify-between px-6 py-5 text-left text-sm font-semibold transition-colors ${
                openIndex === index ? "text-[#f36f8f]" : "text-ink hover:text-ink/70"
              }`}
            >
              <span>{faq.q}</span>
              <ChevronDown
                className={`h-4 w-4 shrink-0 text-soft transition-transform duration-300 ${
                  openIndex === index ? "rotate-180 text-[#f36f8f]" : ""
                }`}
              />
            </button>
            {openIndex === index && (
              <div className="px-6 pb-5">
                <p className="text-sm leading-7 text-soft">{faq.a}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
