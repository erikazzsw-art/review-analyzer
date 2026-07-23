"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRightLeft, Loader2, Search } from "lucide-react";
import { useTranslations } from "next-intl";

import { moveVariant, searchProducts } from "@/lib/api/browser";
import type { ProductSearchItem } from "@/lib/api/types";

type MoveVariantButtonProps = {
  productId: number;
  variantId: number;
  variantName: string;
};

export function MoveVariantButton({ productId, variantId, variantName }: MoveVariantButtonProps) {
  const t = useTranslations("products.moveVariant");
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ProductSearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(
    async (q: string) => {
      if (q.trim().length < 1) {
        setResults([]);
        return;
      }
      setSearching(true);
      try {
        const res = await searchProducts(q.trim());
        setResults((res.items || []).filter((item) => item.id != null && item.id !== productId));
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    },
    [productId],
  );

  useEffect(() => {
    if (!open || !query.trim()) {
      setResults([]);
      return;
    }
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(() => {
      doSearch(query);
    }, 300);
    return () => {
      if (searchTimeout.current) clearTimeout(searchTimeout.current);
    };
  }, [query, open, doSearch]);

  async function handleMove(targetId: number) {
    setSubmitting(true);
    setMessage(null);
    try {
      await moveVariant(productId, variantId, targetId);
      setMessage({ type: "success", text: t("success") });
      setTimeout(() => {
        setOpen(false);
        router.refresh();
      }, 800);
    } catch (err) {
      setMessage({ type: "error", text: (err as { message?: string }).message || t("error") });
    } finally {
      setSubmitting(false);
    }
  }

  function handleClose() {
    setOpen(false);
    setQuery("");
    setResults([]);
    setMessage(null);
  }

  return (
    <>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center justify-center rounded-pill p-1.5 text-soft transition hover:bg-[#f0edff] hover:text-[#7c3aed]"
        aria-label={t("ariaLabel", { name: variantName })}
        title={t("button")}
      >
        <ArrowRightLeft className="h-3.5 w-3.5" />
      </button>

      {/* Modal overlay */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-shell border border-line bg-white p-6 shadow-card">
            <h2 className="font-heading text-lg font-bold text-ink">{t("title")}</h2>
            <p className="mt-1 text-sm text-soft">
              {t("description", { name: variantName })}
            </p>

            {/* Search input */}
            <div className="mt-4 relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2">
                {searching ? (
                  <Loader2 className="h-4 w-4 animate-spin text-soft" />
                ) : (
                  <Search className="h-4 w-4 text-soft" />
                )}
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t("searchPlaceholder")}
                className="w-full rounded-card border border-line bg-white pl-10 pr-4 py-2.5 text-sm outline-none transition focus:border-[#f36f8f]"
                autoFocus
              />
            </div>

            {/* Search results */}
            <div className="mt-3 max-h-60 overflow-y-auto">
              {results.length > 0 ? (
                <div className="space-y-1">
                  {results.map((item) => {
                    const title = item.name || item.parent_product_id || "";

                    return (
                      <button
                        key={item.id ?? item.parent_product_id}
                        type="button"
                        disabled={submitting}
                        onClick={() => handleMove(item.id!)}
                        className="w-full flex items-center justify-between rounded-card border border-line bg-white px-4 py-3 text-left transition hover:border-[#f36f8f]/40 hover:bg-[#faf8fb] disabled:opacity-50"
                      >
                        <div>
                          <p className="text-sm font-semibold text-ink">
                            {title}
                          </p>
                        </div>
                        {submitting && (
                          <Loader2 className="h-4 w-4 animate-spin text-soft" />
                        )}
                      </button>
                    );
                  })}
                </div>
              ) : query.trim() && !searching ? (
                <p className="py-4 text-center text-sm text-soft">{t("noResults")}</p>
              ) : null}
            </div>

            {/* Message */}
            {message && (
              <div
                className={`mt-4 rounded-card border px-4 py-3 text-sm ${
                  message.type === "success"
                    ? "border-[#b7dfd0] bg-[#e8f8f0] text-[#3d8b74]"
                    : "border-[#f5c6cb] bg-[#fff3f5] text-[#b44655]"
                }`}
              >
                {message.text}
              </div>
            )}

            {/* Cancel */}
            <div className="mt-5 flex justify-end">
              <button
                type="button"
                onClick={handleClose}
                disabled={submitting}
                className="rounded-pill border border-line bg-white px-5 py-2.5 text-sm font-semibold text-soft transition hover:bg-gray-50 disabled:opacity-50"
              >
                {t("cancel")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
