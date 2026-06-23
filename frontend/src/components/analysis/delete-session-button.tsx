"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Trash2 } from "lucide-react";

import { deleteSession } from "@/lib/api/browser";

type DeleteSessionButtonProps = {
  sessionId: number;
  sessionTitle: string;
};

export function DeleteSessionButton({
  sessionId,
  sessionTitle,
}: DeleteSessionButtonProps) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteSession(sessionId);
      router.refresh();
    } catch {
      setError("删除失败，请重试");
      setDeleting(false);
    }
  }

  if (confirming) {
    return (
      <div className="inline-flex flex-col gap-2">
        <div className="inline-flex items-center gap-2">
          <span className="text-xs text-[#d94d72]">
            确认删除「{sessionTitle}」？
          </span>
          <button
            type="button"
            disabled={deleting}
            onClick={handleDelete}
            className="inline-flex min-h-9 items-center justify-center rounded-pill bg-[#d94d72] px-4 py-2 text-xs font-semibold text-white shadow-card disabled:opacity-50"
          >
            {deleting ? "删除中…" : "确认删除"}
          </button>
          <button
            type="button"
            disabled={deleting}
            onClick={() => { setConfirming(false); setError(null); }}
            className="inline-flex min-h-9 items-center justify-center rounded-pill border border-line bg-white px-4 py-2 text-xs font-semibold text-soft"
          >
            取消
          </button>
        </div>
        {error ? (
          <span className="text-xs text-[#d94d72]">{error}</span>
        ) : null}
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setConfirming(true)}
      className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-pill border border-line bg-white px-4 py-3 text-sm font-semibold text-[#d94d72] transition hover:border-[#d94d72]/30 hover:bg-[#fff5f7]"
    >
      <Trash2 className="h-4 w-4" />
      删除
    </button>
  );
}
