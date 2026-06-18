"use client";

import { useCallback, useEffect, useState } from "react";

import { submitFeedback } from "@/lib/api/browser";
import type { FeedbackMood, FeedbackType } from "@/lib/api/types";
import { track } from "@/lib/analytics";

import { FeedbackForm } from "./FeedbackForm";
import { FeedbackMoodPicker } from "./FeedbackMoodPicker";

type Stage = "closed" | "mood" | "form" | "submitting" | "success";

const moodToType: Record<FeedbackMood, FeedbackType> = {
  frustrated: "bug",
  idea: "feature",
  love: "general",
};

function getLocale(): "zh" | "en" {
  if (typeof document === "undefined") return "zh";
  const lang = document.documentElement.lang || "zh";
  return lang.startsWith("en") ? "en" : "zh";
}

export function FeedbackWidget() {
  const [stage, setStage] = useState<Stage>("closed");
  const [mood, setMood] = useState<FeedbackMood | null>(null);
  const locale = getLocale();

  const open = useCallback(() => {
    setStage("mood");
    track("feedback_opened");
  }, []);

  const close = useCallback(() => {
    if (stage !== "closed" && stage !== "success") {
      track("feedback_dismissed");
    }
    setStage("closed");
    setMood(null);
  }, [stage]);

  const handleMoodSelect = useCallback((selected: FeedbackMood) => {
    setMood(selected);
    setStage("form");
    track("feedback_mood_selected", { mood: selected });
  }, []);

  const handleSubmit = useCallback(
    async (message: string) => {
      if (!mood) return;
      setStage("submitting");
      try {
        await submitFeedback({
          feedback_type: moodToType[mood],
          mood,
          message: message || null,
          page_path: window.location.pathname,
          user_agent: navigator.userAgent,
        });
        track("feedback_submitted", {
          feedback_type: moodToType[mood],
          mood,
          has_message: !!message,
        });
        setStage("success");
        setTimeout(() => {
          setStage("closed");
          setMood(null);
        }, 2000);
      } catch {
        setStage("form");
      }
    },
    [mood],
  );

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "F") {
        e.preventDefault();
        setStage((prev) => {
          if (prev === "closed") {
            track("feedback_opened");
            return "mood";
          }
          if (prev !== "success") track("feedback_dismissed");
          setMood(null);
          return "closed";
        });
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  if (stage === "closed") {
    return (
      <button
        type="button"
        onClick={open}
        className="fixed bottom-4 right-4 z-50 inline-flex items-center gap-1.5 rounded-pill border border-line bg-white/88 px-3.5 py-2 text-sm font-semibold text-soft shadow-card backdrop-blur transition hover:border-rose hover:text-ink"
      >
        <span className="text-base">💬</span>
        {locale === "zh" ? "反馈" : "Feedback"}
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 w-[300px] rounded-card border border-line bg-white/92 p-4 shadow-card backdrop-blur">
      {stage === "success" ? (
        <div className="flex flex-col items-center gap-2 py-4">
          <span className="text-3xl">✓</span>
          <p className="text-sm font-semibold text-ink">
            {locale === "zh" ? "谢谢反馈！" : "Thanks!"}
          </p>
        </div>
      ) : (
        <>
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-soft">
              {locale === "zh" ? "反馈" : "Feedback"}
            </span>
            <button
              type="button"
              onClick={close}
              className="text-soft hover:text-ink transition text-lg leading-none"
              aria-label="Close"
            >
              ×
            </button>
          </div>
          {stage === "mood" && (
            <FeedbackMoodPicker onSelect={handleMoodSelect} locale={locale} />
          )}
          {(stage === "form" || stage === "submitting") && (
            <FeedbackForm
              pagePath={typeof window !== "undefined" ? window.location.pathname : "/"}
              locale={locale}
              submitting={stage === "submitting"}
              onSubmit={handleSubmit}
              onBack={() => setStage("mood")}
            />
          )}
        </>
      )}
    </div>
  );
}
