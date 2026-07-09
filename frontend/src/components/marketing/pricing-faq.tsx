"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

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
    <section className="mx-auto w-full max-w-3xl px-6 pb-20 lg:px-10">
      <h2 className="font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
        {t("title")}
      </h2>
      <div className="mt-8 divide-y divide-line">
        {faqs.map((faq, index) => (
          <div key={index}>
            <button
              type="button"
              onClick={() =>
                setOpenIndex(openIndex === index ? null : index)
              }
              className="flex w-full items-center justify-between py-5 text-left text-sm font-semibold text-ink transition hover:text-[#4a7dc7]"
            >
              <span>{faq.q}</span>
              <svg
                className={[
                  "h-4 w-4 shrink-0 text-soft transition-transform",
                  openIndex === index ? "rotate-180" : "",
                ].join(" ")}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
            {openIndex === index && (
              <p className="pb-5 text-sm leading-7 text-soft">{faq.a}</p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
