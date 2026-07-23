"use client";

import { useState } from "react";
import { Plus, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";

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

// 见 create-action-panel.tsx 顶部注释：owner_role 后端存中文，UI 仅做显示 i18n。
const OWNER_ROLES = [
  { value: "运营", labelKey: "ownerOps" },
  { value: "产研", labelKey: "ownerProduct" },
  { value: "质检", labelKey: "ownerQA" },
  { value: "复盘", labelKey: "ownerReview" },
] as const;

export function InlineActionButton({
  sessionId,
  productId,
  sourceProductId,
  sourceVersion,
  tag,
  pct,
  reason,
}: InlineActionButtonProps) {
  const t = useTranslations("analysis.action");
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [ownerRole, setOwnerRole] = useState<string>(OWNER_ROLES[0].value);
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
        sourceBatchLabel: t("inlineBatchLabelFormat", { sessionId }),
        currentPct: pct ?? null,
        tagName: tag,
        status: "in_progress",
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
          className="h-6 gap-1 px-1.5 text-[10px] font-medium text-soft"
        >
          <Plus className="h-3 w-3" />
          {t("inlineButton")}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base">{t("inlineDialogTitle")}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <div className="rounded-lg border border-line bg-muted/40 p-3">
            <div className="text-xs font-medium text-soft">{t("inlineSource")}</div>
            <div className="mt-1 text-sm font-semibold text-ink">{tag}</div>
            {pct !== undefined && (
              <div className="mt-0.5 text-xs text-soft">
                {t("inlineMentionedFormat", { pct: pct.toFixed(1) })}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-ink">{t("inlineTitleLabel")}</label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={tag}
              className="h-9"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-ink">{t("inlineOwnerLabel")}</label>
            <div className="flex flex-wrap gap-1.5">
              {OWNER_ROLES.map((role) => (
                <Button
                  key={role.value}
                  variant={ownerRole === role.value ? "default" : "outline"}
                  size="sm"
                  className="h-7 px-3 text-xs"
                  onClick={() => setOwnerRole(role.value)}
                >
                  {t(role.labelKey)}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-medium text-ink">{t("inlineSuggestedLabel")}</label>
            <Textarea
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder={reason || t("inlineSuggestedPlaceholder")}
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
              t("inlineCreated")
            ) : (
              t("inlineCreateBtn")
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
