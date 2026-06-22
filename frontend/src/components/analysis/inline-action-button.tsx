"use client";

import { useState } from "react";
import { Plus, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { createActionItem } from "@/lib/api/browser";
import type { ActionItemCreatePayload } from "@/lib/api/types";

type InlineActionButtonProps = {
  sessionId: number;
  productId?: number | null;
  sourceProductId: string;
  sourceVersion: string;
  tag: string;
  pct?: number;
  reason?: string;
};

const OWNER_OPTIONS = ["运营", "产研", "质检", "复盘"] as const;

export function InlineActionButton({
  sessionId,
  productId,
  sourceProductId,
  sourceVersion,
  tag,
  pct,
  reason,
}: InlineActionButtonProps) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [ownerRole, setOwnerRole] = useState("运营");
  const [action, setAction] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const payload: ActionItemCreatePayload = {
        title: title.trim() || tag,
        ownerRole: ownerRole,
        suggestedAction: action.trim() || reason || "",
        sourceProductId: sourceProductId,
        sourceVersion: sourceVersion,
        sourceBatchLabel: `Session ${sessionId}`,
        currentPct: pct ?? null,
        tagName: tag,
        status: "todo",
      };
      if (productId) {
        payload.productId = productId;
      }
      if (sessionId) {
        payload.sessionId = sessionId;
      }
      await createActionItem(payload);
      setSuccess(true);
      setTimeout(() => {
        setOpen(false);
        setSuccess(false);
        setTitle("");
        setAction("");
      }, 1200);
    } catch {
      // keep dialog open
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 gap-1 px-1.5 text-[10px] font-medium text-soft opacity-0 transition group-hover:opacity-100"
        >
          <Plus className="h-3 w-3" />
          行动
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base">创建行动事项</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <div className="rounded-lg border border-line bg-muted/40 p-3">
            <div className="text-xs font-medium text-soft">来源问题</div>
            <div className="mt-1 text-sm font-semibold text-ink">{tag}</div>
            {pct !== undefined && (
              <div className="mt-0.5 text-xs text-soft">{pct.toFixed(1)}% 的评论提及</div>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-ink">标题</label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={tag}
              className="h-9"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-ink">负责角色</label>
            <div className="flex flex-wrap gap-1.5">
              {OWNER_OPTIONS.map((role) => (
                <Button
                  key={role}
                  variant={ownerRole === role ? "default" : "outline"}
                  size="sm"
                  className="h-7 px-3 text-xs"
                  onClick={() => setOwnerRole(role)}
                >
                  {role}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-ink">建议措施</label>
            <Textarea
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder={reason || "描述改进措施..."}
              className="min-h-[72px] resize-none text-sm"
            />
          </div>

          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || success}
            className="w-full"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : success ? (
              "已创建 ✓"
            ) : (
              "创建行动事项"
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
