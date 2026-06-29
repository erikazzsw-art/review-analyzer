"use client";

import { useState, useEffect, useRef } from "react";
import { X, Check, Loader2 } from "lucide-react";

interface AspectOption {
  key: string;
  label: string;
}

interface LabelCalibrationPopoverProps {
  originalTag: string;
  sessionId?: string;
  commentId?: number;
  subCategory?: string;
  onSubmitted?: () => void;
}

export function LabelCalibrationPopover({
  originalTag,
  sessionId,
  commentId,
  subCategory = "家具家居",
  onSubmitted,
}: LabelCalibrationPopoverProps) {
  const [open, setOpen] = useState(false);
  const [aspects, setAspects] = useState<AspectOption[]>([]);
  const [correctTag, setCorrectTag] = useState("");
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open || aspects.length > 0) return;
    fetch("/api/taxonomy/aspects", { credentials: "include" })
      .then((r) => r.json())
      .then((data: AspectOption[]) => setAspects(data))
      .catch(() => {});
  }, [open, aspects.length]);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const res = await fetch("/api/calibration", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original_tag: originalTag,
          correct_tag: correctTag || null,
          note: note || null,
          session_id: sessionId || null,
          comment_id: commentId || null,
          sub_category: subCategory,
        }),
      });
      if (res.ok) {
        setSubmitted(true);
        onSubmitted?.();
        setTimeout(() => setOpen(false), 800);
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <span className="inline-flex items-center text-emerald-600 text-[10px]">
        <Check className="h-3 w-3" />
      </span>
    );
  }

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="ml-1 inline-flex items-center justify-center h-4 w-4 rounded text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10 transition-colors"
        title="标记标签不准确"
      >
        <X className="h-2.5 w-2.5" />
      </button>

      {open && (
        <div
          ref={panelRef}
          className="absolute left-0 top-5 z-50 w-60 rounded-md border bg-popover p-3 shadow-md"
        >
          <div className="text-xs font-medium mb-2 text-foreground">
            标签校准：<span className="text-destructive">{originalTag}</span>
          </div>

          <label className="text-[11px] text-muted-foreground mb-1 block">
            正确标签
          </label>
          <select
            value={correctTag}
            onChange={(e) => setCorrectTag(e.target.value)}
            className="w-full h-7 rounded border border-input bg-background px-2 text-xs mb-2"
          >
            <option value="">— 选择正确标签 —</option>
            {aspects
              .filter((a) => a.key !== originalTag)
              .map((a) => (
                <option key={a.key} value={a.key}>
                  {a.label}（{a.key}）
                </option>
              ))}
          </select>

          <label className="text-[11px] text-muted-foreground mb-1 block">
            备注（可选）
          </label>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="下拉无匹配时填写"
            className="w-full h-7 rounded border border-input bg-background px-2 text-xs mb-3"
          />

          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting || (!correctTag && !note)}
            className="w-full h-7 rounded bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50 flex items-center justify-center gap-1"
          >
            {submitting ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              "提交校准"
            )}
          </button>
        </div>
      )}
    </span>
  );
}
