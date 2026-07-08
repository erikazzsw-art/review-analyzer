"use client";

import { useTranslations } from "next-intl";

type QaSuggestCardsProps = {
  onSelect: (question: string) => void;
};

export function QaSuggestCards({ onSelect }: QaSuggestCardsProps) {
  const t = useTranslations("analysis.qa");
  const suggestions = [
    t("suggest1"),
    t("suggest2"),
    t("suggest3"),
    t("suggest4"),
  ];

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4">
      <h2 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
        {t("suggestTitle")}
      </h2>
      <p className="mt-2 text-sm leading-7 text-soft">
        {t("suggestSubtitle")}
      </p>
      <div className="mt-8 grid w-full max-w-2xl gap-3 sm:grid-cols-2">
        {suggestions.map((text) => (
          <button
            key={text}
            type="button"
            onClick={() => onSelect(text)}
            className="rounded-card border border-line bg-white px-4 py-4 text-left text-sm leading-6 text-ink transition hover:border-[#f36f8f] hover:shadow-card"
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}
