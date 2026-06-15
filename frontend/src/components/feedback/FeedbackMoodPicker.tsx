"use client";

import type { FeedbackMood } from "@/lib/api/types";

type MoodOption = {
  mood: FeedbackMood;
  emoji: string;
  labelZh: string;
  labelEn: string;
};

const moods: MoodOption[] = [
  { mood: "frustrated", emoji: "😤", labelZh: "Bug", labelEn: "Bug" },
  { mood: "idea", emoji: "💡", labelZh: "建议", labelEn: "Idea" },
  { mood: "love", emoji: "❤️", labelZh: "喜欢", labelEn: "Love" },
];

type Props = {
  onSelect: (mood: FeedbackMood) => void;
  locale: "zh" | "en";
};

export function FeedbackMoodPicker({ onSelect, locale }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm font-semibold text-ink">
        {locale === "zh" ? "你的体验如何？" : "How's your experience?"}
      </p>
      <div className="flex gap-2">
        {moods.map((m) => (
          <button
            key={m.mood}
            type="button"
            onClick={() => onSelect(m.mood)}
            className="flex flex-1 flex-col items-center gap-1 rounded-xl border border-line bg-white/60 px-3 py-3 transition hover:border-rose hover:bg-roseSoft"
          >
            <span className="text-2xl">{m.emoji}</span>
            <span className="text-xs font-medium text-soft">
              {locale === "zh" ? m.labelZh : m.labelEn}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
