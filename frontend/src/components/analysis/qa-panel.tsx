"use client";

import { useCallback, useState } from "react";

import { createQaConversation, sendQaMessage } from "@/lib/api/browser";
import type { QaProduct } from "@/lib/api/types";

import { QaChatArea, type ChatMessage } from "./qa-chat-area";
import { QaInputBar } from "./qa-input-bar";
import { QaSuggestCards } from "./qa-suggest-cards";

type QaPanelProps = {
  products: QaProduct[];
};

export function QaPanel({ products }: QaPanelProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>(
    products.slice(0, 1).map((p) => p.parent_product_id),
  );
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSuggestSelect = useCallback((text: string) => {
    setQuestion(text);
  }, []);

  const handleSubmit = useCallback(async () => {
    const q = question.trim();
    if (!q || selectedIds.length === 0 || isSubmitting) return;

    setError("");
    setIsSubmitting(true);

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: q,
    };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");

    try {
      let convId = conversationId;
      if (!convId) {
        const conv = await createQaConversation(selectedIds);
        convId = conv.id;
        setConversationId(convId);
      }

      const response = await sendQaMessage(convId, q);
      const assistantMsg: ChatMessage = {
        id: `assistant-${response.id}`,
        role: "assistant",
        content: response.content,
        citations: response.citations,
        retrieval_method: response.retrieval_method,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "问答失败");
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
      setQuestion(q);
    } finally {
      setIsSubmitting(false);
    }
  }, [question, selectedIds, isSubmitting, conversationId]);

  const handleProductsChange = useCallback(
    (ids: string[]) => {
      setSelectedIds(ids);
      if (conversationId && ids.sort().join(",") !== selectedIds.sort().join(",")) {
        setConversationId(null);
        setMessages([]);
      }
    },
    [conversationId, selectedIds],
  );

  return (
    <section className="flex h-[calc(100vh-8rem)] flex-col rounded-shell border border-line bg-white/84 shadow-card backdrop-blur">
      {messages.length === 0 ? (
        <QaSuggestCards onSelect={handleSuggestSelect} />
      ) : (
        <QaChatArea messages={messages} isLoading={isSubmitting} />
      )}

      {error && (
        <div className="mx-4 mb-2 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-2 text-sm text-[#b44655]">
          {error}
        </div>
      )}

      <QaInputBar
        products={products}
        selectedIds={selectedIds}
        onProductsChange={handleProductsChange}
        value={question}
        onChange={setQuestion}
        onSubmit={handleSubmit}
        disabled={isSubmitting}
      />
    </section>
  );
}
