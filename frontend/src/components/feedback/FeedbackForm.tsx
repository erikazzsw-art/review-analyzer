"use client";

import { useState } from "react";

type Props = {
  pagePath: string;
  locale: "zh" | "en";
  submitting: boolean;
  onSubmit: (message: string) => void;
  onBack: () => void;
};

export function FeedbackForm({ pagePath, locale, submitting, onSubmit, onBack }: Props) {
  const [message, setMessage] = useState("");

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          className="text-sm text-soft hover:text-ink transition"
          aria-label="Back"
        >
          ←
        </button>
        <span className="inline-flex rounded-pill bg-roseSoft px-2.5 py-0.5 text-[11px] font-medium text-rose">
          {pagePath}
        </span>
      </div>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value.slice(0, 500))}
        placeholder={
          locale === "zh"
            ? "简单说说（可跳过）"
            : "Tell us more (optional)"
        }
        rows={3}
        className="w-full resize-none rounded-xl border border-line bg-white/60 px-3 py-2.5 text-sm text-ink placeholder:text-soft/60 focus:border-rose focus:outline-none"
      />
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-soft">{message.length}/500</span>
        <button
          type="button"
          disabled={submitting}
          onClick={() => onSubmit(message)}
          className="inline-flex items-center justify-center rounded-pill bg-gradient-to-r from-rose to-lavender px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:opacity-90 disabled:opacity-50"
        >
          {submitting
            ? locale === "zh" ? "提交中..." : "Sending..."
            : locale === "zh" ? "提交" : "Submit"}
        </button>
      </div>
    </div>
  );
}
