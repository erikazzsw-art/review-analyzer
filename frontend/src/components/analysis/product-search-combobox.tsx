"use client";

import { useEffect, useRef, useState } from "react";
import { Search, ChevronDown } from "lucide-react";

import { searchProducts } from "@/lib/api/browser";
import type { ProductSearchItem } from "@/lib/api/types";

type Props = {
  value: string;
  onChange: (productId: string) => void;
  placeholder?: string;
};

export function ProductSearchCombobox({ value, onChange, placeholder }: Props) {
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

  const handleSelect = (pid: string) => {
    onChange(pid);
    setOpen(false);
    setQuery("");
    inputRef.current?.blur();
  };

  const display = open ? query : value;

  return (
    <div ref={containerRef} className="relative w-full max-w-xs">
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
          placeholder={placeholder || "搜索产品编码 / 名称"}
          className="h-9 w-full rounded-pill border border-line bg-white pl-9 pr-9 text-sm font-medium text-ink shadow-sm focus:border-rose focus:outline-none focus:ring-2 focus:ring-rose/20"
        />
        <ChevronDown
          className={`pointer-events-none absolute right-3 h-4 w-4 text-soft transition-transform ${open ? "rotate-180" : ""}`}
        />
      </div>
      {open && (
        <ul className="absolute left-0 right-0 z-50 mt-1 max-h-72 overflow-auto rounded-card border border-line bg-white py-1 shadow-card">
          {loading && (
            <li className="px-3 py-2 text-xs text-soft">加载中…</li>
          )}
          {!loading && items.length === 0 && (
            <li className="px-3 py-2 text-xs text-soft">
              {query ? `未找到 “${query}” 相关产品` : "暂无产品"}
            </li>
          )}
          {!loading &&
            items.map((it) => (
              <li
                key={it.parent_product_id}
                onClick={() => handleSelect(it.parent_product_id)}
                className={`cursor-pointer px-3 py-2 hover:bg-[#faf8fb] ${
                  it.parent_product_id === value ? "bg-[#f3f0f5]" : ""
                }`}
              >
                <div className="text-sm font-semibold text-ink">{it.parent_product_id}</div>
                <div className="mt-0.5 flex items-center gap-2 text-xs text-soft">
                  {it.name && <span className="truncate">{it.name}</span>}
                  <span className="shrink-0">{it.review_count} 评论</span>
                  {it.session_count > 0 && (
                    <span className="shrink-0">· {it.session_count} 批</span>
                  )}
                </div>
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
