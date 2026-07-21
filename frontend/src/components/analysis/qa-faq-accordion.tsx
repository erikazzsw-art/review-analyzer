"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";
import Link from "next/link";

export function QaFaqAccordion() {
  const t = useTranslations("analysis.qa");
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const faqItems: Array<{ question: string; answer: string }> = Array.from(
    { length: 8 },
    (_, i) => ({
      question: t(`faq.${i}.question`),
      answer: t(`faq.${i}.answer`),
    }),
  );

  const toggleItem = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section className="flex flex-col gap-4">
      <h2 className="font-heading text-xl font-extrabold tracking-[-0.03em] text-ink md:text-2xl">
        {t("faqTitle")}
      </h2>

      <div className="flex flex-col gap-3">
        {faqItems.map((item, index) => {
          const isOpen = openIndex === index;
          return (
            <div
              key={index}
              className={`glass-white cursor-pointer px-5 py-4 transition-all duration-300 ${
                isOpen
                  ? "shadow-glow ring-1 ring-rose/20"
                  : "hover:shadow-card"
              }`}
              onClick={() => toggleItem(index)}
            >
              {/* Question row */}
              <div className="flex items-center justify-between gap-4">
                <span
                  className={`text-sm font-semibold leading-snug transition-colors duration-300 md:text-base ${
                    isOpen ? "text-rose" : "text-ink"
                  }`}
                >
                  {item.question}
                </span>
                <ChevronDown
                  className={`h-5 w-5 flex-shrink-0 text-soft transition-all duration-300 ${
                    isOpen ? "rotate-180 text-rose" : ""
                  }`}
                />
              </div>

              {/* Answer */}
              <div
                className={`grid transition-all duration-300 ${
                  isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                }`}
              >
                <div className="overflow-hidden">
                  <p className="pt-3 text-sm leading-7 text-soft">
                    {item.answer}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Contact link */}
      <p className="text-center text-sm text-soft">
        {t.rich("faqContact", {
          link: (chunks) => (
            <Link
              href="/contact"
              className="font-medium text-rose underline underline-offset-2 transition-colors hover:text-rose/80"
            >
              {chunks}
            </Link>
          ),
        })}
      </p>
    </section>
  );
}
