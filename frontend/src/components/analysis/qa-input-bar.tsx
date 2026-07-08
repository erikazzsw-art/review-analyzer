"use client";

import { useRef, useCallback, type KeyboardEvent } from "react";
import { useTranslations } from "next-intl";

import type { QaProduct } from "@/lib/api/types";
import { QaProductSelector } from "./qa-product-selector";

type QaInputBarProps = {
  products: QaProduct[];
  selectedIds: string[];
  onProductsChange: (ids: string[]) => void;
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
};

export function QaInputBar({
  products,
  selectedIds,
  onProductsChange,
  value,
  onChange,
  onSubmit,
  disabled,
}: QaInputBarProps) {
  const t = useTranslations("analysis.qa");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const selectedProducts = products.filter((p) => selectedIds.includes(p.parent_product_id));

  function removeProduct(pid: string) {
    onProductsChange(selectedIds.filter((id) => id !== pid));
  }

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (!disabled && value.trim() && selectedIds.length > 0) {
          onSubmit();
        }
      }
    },
    [disabled, value, selectedIds.length, onSubmit],
  );

  return (
    <div className="border-t border-line bg-white px-4 py-3">
      {selectedProducts.length > 0 && (
        <div className="mb-2 flex flex-wrap items-center gap-1.5">
          {selectedProducts.map((p) => (
            <span
              key={p.parent_product_id}
              className="inline-flex items-center gap-1 rounded-full bg-[#eef6ff] px-2.5 py-1 text-xs font-medium text-[#4a7dc7]"
            >
              {p.name || p.parent_product_id}
              <button
                type="button"
                onClick={() => removeProduct(p.parent_product_id)}
                className="ml-0.5 text-[#4a7dc7]/60 hover:text-[#4a7dc7]"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2">
        <QaProductSelector
          products={products}
          selectedIds={selectedIds}
          onConfirm={onProductsChange}
        />

        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={selectedIds.length > 0 ? t("inputPlaceholder") : t("inputSelectFirst")}
            rows={1}
            disabled={disabled}
            className="max-h-32 min-h-[40px] w-full resize-none rounded-card border border-line bg-[#f9fafb] px-4 py-2.5 text-sm outline-none transition focus:border-[#f36f8f] disabled:opacity-60"
          />
        </div>

        <button
          type="button"
          onClick={onSubmit}
          disabled={disabled || !value.trim() || selectedIds.length === 0}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink text-white shadow-card transition disabled:opacity-40"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 8h12M9 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </div>
  );
}
