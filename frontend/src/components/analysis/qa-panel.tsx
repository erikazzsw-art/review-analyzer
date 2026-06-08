"use client";

import { useMemo, useState } from "react";

import { askReviews } from "@/lib/api/browser";
import type { QaProduct } from "@/lib/api/types";

type QaPanelProps = {
  products: QaProduct[];
};

export function QaPanel({ products }: QaPanelProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>(products.slice(0, 1).map((item) => item.parent_product_id));
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<
    Array<{ id: number | null; product_id: string | null; version: string | null; session_id: number | null; date: string | null; rating: number | null; content: string | null; issue_tag: string | null; highlight_tag: string | null; sentiment: string | null; }>
  >([]);
  const [retrievalMethod, setRetrievalMethod] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit = useMemo(() => selectedIds.length > 0 && question.trim().length > 0, [question, selectedIds.length]);

  function toggleProduct(productId: string): void {
    setSelectedIds((current) =>
      current.includes(productId)
        ? current.filter((item) => item !== productId)
        : [...current, productId].slice(0, 5),
    );
  }

  async function handleAsk(): Promise<void> {
    if (!canSubmit) {
      setError("请先选择产品并输入问题。");
      return;
    }

    setError("");
    setIsSubmitting(true);
    try {
      const response = await askReviews({
        productIds: selectedIds,
        question: question.trim(),
        topK: 5,
      });
      setAnswer(response.answer);
      setRetrievalMethod(response.retrieval_method);
      setCitations(response.citations);
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "问答失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            REVIEW Q&A
          </div>
          <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            问评论
          </h3>
          <p className="mt-2 text-sm leading-7 text-soft">
            先选 1-5 个产品，再围绕这些产品的评论提问。回答会返回引用评论，便于回看证据。
          </p>
        </div>
        <div className="rounded-card border border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
          可选产品：{products.length} 个
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {products.map((product) => {
          const isActive = selectedIds.includes(product.parent_product_id);
          return (
            <button
              type="button"
              key={product.parent_product_id}
              onClick={() => toggleProduct(product.parent_product_id)}
              className={[
                "rounded-card border px-4 py-4 text-left transition",
                isActive ? "border-transparent bg-ink text-white shadow-card" : "border-line bg-white text-ink hover:border-[#f36f8f]",
              ].join(" ")}
            >
              <div className="text-sm font-semibold">{product.name || product.parent_product_id}</div>
              <div className={["mt-2 text-xs leading-6", isActive ? "text-white/80" : "text-soft"].join(" ")}>
                {product.parent_product_id} · {product.review_count} 条评论 · 差评率 {product.negative_rate.toFixed(1)}%
              </div>
            </button>
          );
        })}
      </div>

      <label className="mt-5 block space-y-2">
        <span className="text-sm font-semibold text-ink">问题</span>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="例如：哪几个产品最常被吐槽安装困难？"
          className="min-h-28 w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
        />
      </label>

      <div className="mt-4 flex items-center justify-between gap-4">
        <div className="text-sm leading-7 text-soft">
          当前选择：{selectedIds.length} 个产品
        </div>
        <button
          type="button"
          onClick={handleAsk}
          disabled={!canSubmit || isSubmitting}
          className="inline-flex min-h-12 items-center justify-center rounded-pill bg-ink px-6 py-3 text-sm font-semibold text-white shadow-card transition disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "检索中..." : "开始提问"}
        </button>
      </div>

      {error ? (
        <div className="mt-4 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]">
          {error}
        </div>
      ) : null}

      {answer ? (
        <div className="mt-6 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-card border border-line bg-white px-5 py-5">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              回答
            </div>
            <p className="mt-3 text-sm leading-7 text-ink whitespace-pre-line">{answer}</p>
            <div className="mt-4 text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              检索方式
            </div>
            <div className="mt-2 text-sm leading-7 text-ink">
              {retrievalMethod === "vector" ? "向量检索" : "文本检索"}
            </div>
          </div>
          <div className="rounded-card border border-line bg-[#f8fffc] px-5 py-5">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              引用评论
            </div>
            <div className="mt-3 space-y-3">
              {citations.length > 0 ? (
                citations.map((item, index) => (
                  <div key={`${item.id ?? index}`} className="rounded-card border border-line bg-white px-4 py-4 text-sm leading-7 text-ink">
                    <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                      {item.product_id || "--"} · {item.version || "--"} · 批次 {item.session_id || "--"}
                    </div>
                    <div className="mt-2 text-sm leading-7 text-ink">
                      {item.content || ""}
                    </div>
                    <div className="mt-2 text-xs leading-6 text-soft">
                      {item.date || "无日期"} · {item.sentiment || "--"} · {item.issue_tag || item.highlight_tag || "—"}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-sm leading-7 text-soft">暂无引用。</div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
