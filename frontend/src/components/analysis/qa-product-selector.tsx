"use client";

import { useMemo, useRef, useState, useEffect } from "react";

import type { QaProduct } from "@/lib/api/types";

type QaProductSelectorProps = {
  products: QaProduct[];
  selectedIds: string[];
  onConfirm: (ids: string[]) => void;
};

export function QaProductSelector({ products, selectedIds, onConfirm }: QaProductSelectorProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [localSelected, setLocalSelected] = useState<string[]>(selectedIds);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLocalSelected(selectedIds);
  }, [selectedIds]);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return products;
    return products.filter(
      (p) =>
        (p.name || "").toLowerCase().includes(q) ||
        p.parent_product_id.toLowerCase().includes(q),
    );
  }, [products, search]);

  function toggleProduct(pid: string) {
    setLocalSelected((current) =>
      current.includes(pid)
        ? current.filter((id) => id !== pid)
        : current.length >= 5
          ? current
          : [...current, pid],
    );
  }

  function handleConfirm() {
    onConfirm(localSelected);
    setOpen(false);
    setSearch("");
  }

  return (
    <div className="relative" ref={popoverRef}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex h-7 w-7 items-center justify-center rounded-full border border-line bg-white text-soft transition hover:border-[#f36f8f] hover:text-ink"
        title="选择产品"
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div className="absolute bottom-full left-0 z-50 mb-2 w-80 rounded-card border border-line bg-white shadow-lg">
          <div className="border-b border-line px-3 py-2">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索产品名或 ASIN..."
              className="w-full rounded border border-line bg-[#f9fafb] px-3 py-1.5 text-sm outline-none focus:border-[#f36f8f]"
              autoFocus
            />
          </div>
          <div className="max-h-60 overflow-y-auto px-1 py-1">
            {filtered.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-soft">未找到匹配产品</div>
            ) : (
              filtered.map((product) => {
                const isActive = localSelected.includes(product.parent_product_id);
                return (
                  <button
                    key={product.parent_product_id}
                    type="button"
                    onClick={() => toggleProduct(product.parent_product_id)}
                    className={[
                      "flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm transition",
                      isActive ? "bg-[#eef6ff] text-ink" : "text-ink hover:bg-[#f9fafb]",
                    ].join(" ")}
                  >
                    <span
                      className={[
                        "flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px]",
                        isActive ? "border-[#4a7dc7] bg-[#4a7dc7] text-white" : "border-line",
                      ].join(" ")}
                    >
                      {isActive && "✓"}
                    </span>
                    <span className="flex-1 truncate font-medium">
                      {product.name || product.parent_product_id}
                    </span>
                    <span className="shrink-0 text-xs text-soft">
                      {product.review_count} 条
                    </span>
                  </button>
                );
              })
            )}
          </div>
          <div className="flex items-center justify-between border-t border-line px-3 py-2">
            <span className="text-xs text-soft">已选 {localSelected.length}/5</span>
            <button
              type="button"
              onClick={handleConfirm}
              className="rounded-pill bg-ink px-4 py-1.5 text-xs font-semibold text-white transition hover:opacity-90"
            >
              确认
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
