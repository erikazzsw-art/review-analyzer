"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Trash2 } from "lucide-react";

import { deleteVariant } from "@/lib/api/browser";

type DeleteVariantButtonProps = {
  productId: number;
  variantId: number;
  variantName: string;
};

export function DeleteVariantButton({ productId, variantId, variantName }: DeleteVariantButtonProps) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteVariant(productId, variantId);
      router.refresh();
    } catch {
      setDeleting(false);
      setConfirming(false);
    }
  }

  if (confirming) {
    return (
      <div className="inline-flex items-center gap-2">
        <span className="text-xs text-[#d94d72]">确认？</span>
        <button
          type="button"
          disabled={deleting}
          onClick={handleDelete}
          className="rounded-pill bg-[#d94d72] px-3 py-1 text-xs font-semibold text-white disabled:opacity-50"
        >
          {deleting ? "删除中…" : "删除"}
        </button>
        <button
          type="button"
          disabled={deleting}
          onClick={() => setConfirming(false)}
          className="rounded-pill border border-line bg-white px-3 py-1 text-xs font-semibold text-soft"
        >
          取消
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setConfirming(true)}
      aria-label={`删除变体 ${variantName}`}
      className="inline-flex items-center justify-center rounded-pill p-1.5 text-soft transition hover:bg-[#fff5f7] hover:text-[#d94d72]"
    >
      <Trash2 className="h-3.5 w-3.5" />
    </button>
  );
}
