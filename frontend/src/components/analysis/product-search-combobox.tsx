"use client";

import { useEffect, useRef, useState } from "react";
import { Search, ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";

import { searchProducts } from "@/lib/api/browser";
import type { ProductSearchItem } from "@/lib/api/types";

type MatchedVariant = {
  child_asin: string;
  name: string | null;
};

type Props = {
  value: string;
  variantAsin?: string | null;
  onChange: (productId: string, options?: { variantAsin?: string | null }) => void;
  placeholder?: string;
};

export function ProductSearchCombobox({ value, variantAsin, onChange, placeholder }: Props) {
  const t = useTranslations("analysis.productSearch");
  const tCommon = useTranslations("common");
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<ProductSearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    const ctl = new AbortController();
    setLoading(true);
    const timer = window.setTimeout(() => {
      searchProducts(query, 20)
        .then((res) => {
          if (ctl.signal.aborted) return;
          setItems(res.items);
        })
        .catch(() => {
          if (!ctl.signal.aborted) setItems([]);
        })
        .finally(() => {
          if (!ctl.signal.aborted) setLoading(false);
        });
    }, 200);
    return () => {
      ctl.abort();
      window.clearTimeout(timer);
    };
  }, [query, open]);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const findMatchedVariant = (item: ProductSearchItem): MatchedVariant | null => {
    const q = query.trim().toLowerCase();
    if (!q) return null;
    const variants = item.variants || [];
    const matches = (variant: MatchedVariant) => {
      const asin = variant.child_asin.toLowerCase();
      const name = (variant.name || "").toLowerCase();
      return asin === q || name === q;
    };
    const startsWith = (variant: MatchedVariant) => {
      const asin = variant.child_asin.toLowerCase();
      const name = (variant.name || "").toLowerCase();
      return asin.startsWith(q) || name.startsWith(q);
    };
    const includes = (variant: MatchedVariant) => {
      const asin = variant.child_asin.toLowerCase();
      const name = (variant.name || "").toLowerCase();
      return asin.includes(q) || name.includes(q);
    };
    return (
      variants.find(matches) ||
      variants.find(startsWith) ||
      variants.find(includes) ||
      null
    );
  };

  const handleSelect = (pid: string, selectedVariantAsin?: string | null) => {
    onChange(pid, { variantAsin: selectedVariantAsin || null });
    setOpen(false);
    setQuery("");
    inputRef.current?.blur();
  };

  const selectItem = (item: ProductSearchItem) => {
    handleSelect(item.parent_product_id, findMatchedVariant(item)?.child_asin || null);
  };

  const display = open ? query : variantAsin || value;

  return (
    <div ref={containerRef} className="relative w-full max-w-sm">
      <div className="relative flex items-center">
        <Search className="pointer-events-none absolute left-3 h-4 w-4 text-soft" />
        <input
          ref={inputRef}
          type="text"
          value={display}
          onFocus={() => {
            setOpen(true);
            setQuery("");
          }}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!open) setOpen(true);
          }}
          onKeyDown={(e) => {
            if (e.key !== "Enter" || items.length === 0) return;
            e.preventDefault();
            selectItem(items[0]);
          }}
          placeholder={placeholder || t("placeholder")}
          className="h-9 w-full rounded-pill border border-line bg-white pl-9 pr-9 text-sm font-medium text-ink shadow-sm placeholder:text-soft/60 focus:border-rose focus:outline-none focus:ring-2 focus:ring-rose/20"
        />
        <ChevronDown
          className={`pointer-events-none absolute right-3 h-4 w-4 text-soft transition-transform ${open ? "rotate-180" : ""}`}
        />
      </div>
      {open && (
        <ul className="absolute left-0 right-0 z-50 mt-1 max-h-72 overflow-auto rounded-card border border-line bg-white py-1 shadow-card">
          {loading && (
            <li className="px-3 py-2 text-xs text-soft">{tCommon("loadingEllipsis")}</li>
          )}
          {!loading && items.length === 0 && (
            <li className="px-3 py-2 text-xs text-soft">
              {query ? t("notFoundFormat", { query }) : t("empty")}
            </li>
          )}
          {!loading &&
            items.map((it) => {
              const matchedVariant = findMatchedVariant(it);
              const variantCount = (it.variants || []).filter((variant) => variant.child_asin).length;
              const secondaryLabel = matchedVariant
                ? [it.parent_product_id, it.name].filter(Boolean).join(" · ")
                : it.name;
              const primaryLabel = matchedVariant?.name || matchedVariant?.child_asin || it.parent_product_id;

              return (
                <li
                  key={it.parent_product_id}
                  onClick={() => selectItem(it)}
                  className={`cursor-pointer px-3 py-2.5 hover:bg-[#faf8fb] ${
                    it.parent_product_id === value ? "bg-[#f3f0f5]" : ""
                  }`}
                >
                  <div className="truncate text-sm font-semibold text-ink">
                    {primaryLabel}
                  </div>
                  {secondaryLabel && (
                    <div className="mt-0.5 truncate text-xs text-soft">{secondaryLabel}</div>
                  )}
                  {(matchedVariant || variantCount > 0) && (
                    <div className="mt-1 flex flex-wrap items-center gap-1">
                      <span className="text-[10px] font-semibold uppercase text-soft">ASIN</span>
                      {matchedVariant ? (
                        <span
                          key={matchedVariant.child_asin}
                          className="rounded bg-[#f3f0f5] px-1.5 py-0.5 font-mono text-[10px] font-semibold text-ink/75"
                        >
                          {matchedVariant.child_asin}
                        </span>
                      ) : (
                        <span className="text-[10px] font-semibold text-soft">
                          {variantCount}
                        </span>
                      )}
                    </div>
                  )}
                  <div className="mt-1 flex items-center gap-2 text-xs text-soft">
                    <span>
                      {it.review_count} {t("reviewsUnit")}
                    </span>
                    {it.session_count > 0 && (
                      <span>
                        · {it.session_count} {t("sessionsUnit")}
                      </span>
                    )}
                  </div>
                </li>
              );
            })}
        </ul>
      )}
    </div>
  );
}
