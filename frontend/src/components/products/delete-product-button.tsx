"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { deleteProduct } from "@/lib/api/browser";

type DeleteProductButtonProps = {
  productId: number;
  productName: string;
};

export function DeleteProductButton({ productId, productName }: DeleteProductButtonProps) {
  const t = useTranslations("products.delete");
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteProduct(productId);
      router.refresh();
    } catch (err) {
      console.error("Delete product failed:", err);
      setDeleting(false);
      setConfirming(false);
    }
  }

  if (confirming) {
    return (
      <div className="inline-flex items-center gap-2">
        <span className="text-xs text-[#d94d72]">
          {t("confirmText", { name: productName })}
        </span>
        <button
          type="button"
          disabled={deleting}
          onClick={handleDelete}
          className="inline-flex min-h-9 items-center justify-center rounded-pill bg-[#d94d72] px-4 py-2 text-xs font-semibold text-white shadow-card disabled:opacity-50"
        >
          {deleting ? t("deleting") : t("confirmDelete")}
        </button>
        <button
          type="button"
          disabled={deleting}
          onClick={() => setConfirming(false)}
          className="inline-flex min-h-9 items-center justify-center rounded-pill border border-line bg-white px-4 py-2 text-xs font-semibold text-soft"
        >
          {t("cancelButton")}
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setConfirming(true)}
      className="inline-flex min-h-9 items-center justify-center gap-1.5 rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-[#d94d72] transition hover:border-[#d94d72]/30 hover:bg-[#fff5f7]"
    >
      <Trash2 className="h-3.5 w-3.5" />
      {t("deleteButton")}
    </button>
  );
}
