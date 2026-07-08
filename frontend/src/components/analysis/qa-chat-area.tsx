"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import type { QaCitation, QaMessage } from "@/lib/api/types";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: QaCitation[];
  retrieval_method?: string | null;
  intent?: string | null;
};

const INTENT_KEYS: Record<string, string> = {
  aggregate_feedback: "intentAgg",
  product_compare: "intentCompare",
  rating_breakdown: "intentRating",
  consumer_insight: "intentInsight",
  trend_and_emerging: "intentTrend",
  specific_retrieval: "intentRetrieve",
  unanswerable: "intentUnanswer",
};

const RETRIEVAL_KEYS: Record<string, string> = {
  hybrid: "retrievalHybrid",
  vector: "retrievalVector",
  aggregation: "retrievalAggregation",
  compare: "retrievalCompare",
  fallback: "retrievalFallback",
};

type QaChatAreaProps = {
  messages: ChatMessage[];
  isLoading?: boolean;
};

export type { ChatMessage };

export function QaChatArea({ messages, isLoading }: QaChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto max-w-3xl space-y-6">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isLoading && <LoadingSkeleton />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const t = useTranslations("analysis.qa");

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-[#f0f4f8] px-4 py-3 text-sm leading-7 text-ink">
          {message.content}
        </div>
      </div>
    );
  }

  const intentKey = message.intent ? INTENT_KEYS[message.intent] : undefined;
  const retrievalKey = message.retrieval_method ? RETRIEVAL_KEYS[message.retrieval_method] : undefined;

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%]">
        <div className="whitespace-pre-line text-sm leading-7 text-ink">
          {message.content}
        </div>
        {(message.intent || message.retrieval_method) && (
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-soft">
            {intentKey && (
              <span className="rounded-full bg-[#fdf1f4] px-2 py-0.5 font-medium text-[#d94d72]">
                {t(intentKey)}
              </span>
            )}
            {message.retrieval_method && (
              <span>
                {retrievalKey
                  ? t(retrievalKey)
                  : t("retrievalOther", { method: message.retrieval_method })}
              </span>
            )}
          </div>
        )}
        {message.citations && message.citations.length > 0 && (
          <CitationsCollapse citations={message.citations} />
        )}
      </div>
    </div>
  );
}

function CitationsCollapse({ citations }: { citations: QaCitation[] }) {
  const t = useTranslations("analysis.qa");
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="text-xs font-medium text-[#4a7dc7] hover:underline"
      >
        {expanded ? t("citationCollapse") : t("citationExpand", { count: citations.length })}
      </button>
      {expanded && (
        <div className="mt-2 space-y-2">
          {citations.map((c, i) => (
            <div
              key={c.id ?? i}
              className="rounded-card border border-line bg-[#f9fafb] px-3 py-2.5 text-xs leading-6 text-ink"
            >
              <div className="font-medium text-soft">
                {c.product_id || "—"} · {c.date || t("noDate")} · {c.sentiment || "—"}
              </div>
              <div className="mt-1">{c.content || ""}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex justify-start">
      <div className="space-y-2">
        <div className="h-4 w-48 animate-pulse rounded bg-[#e5e7eb]" />
        <div className="h-4 w-64 animate-pulse rounded bg-[#e5e7eb]" />
        <div className="h-4 w-36 animate-pulse rounded bg-[#e5e7eb]" />
      </div>
    </div>
  );
}
