"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type MeData = { username: string; email?: string; plan: string; created_at?: string };

type SystemSettingsDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function SystemSettingsDialog({ open, onOpenChange }: SystemSettingsDialogProps) {
  const t = useTranslations("systemSettingsDialog");
  const locale = useLocale();
  const [me, setMe] = useState<MeData | null>(null);

  const planLabels: Record<string, string> = {
    free: "Free",
    starter: "Starter",
    pro: "Pro",
    team: "Team",
  };

  useEffect(() => {
    if (!open) return;
    fetch("/api/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setMe(d as MeData); })
      .catch(() => {});
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md rounded-xl border border-line bg-white p-6 shadow-card">
        <DialogHeader>
          <DialogTitle className="text-lg font-bold text-ink">{t("title")}</DialogTitle>
        </DialogHeader>

        <div className="mt-4">
          <h3 className="text-sm font-semibold text-ink">{t("accountInfo")}</h3>
          {me ? (
            <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-soft">{t("username")}</dt>
                <dd className="font-medium text-ink">{me.username}</dd>
              </div>
              {me.email && (
                <div>
                  <dt className="text-soft">{t("email")}</dt>
                  <dd className="font-medium text-ink">{me.email}</dd>
                </div>
              )}
              <div>
                <dt className="text-soft">{t("currentPlan")}</dt>
                <dd className="font-medium text-ink">{planLabels[me.plan] ?? me.plan}</dd>
              </div>
              {me.created_at && (
                <div>
                  <dt className="text-soft">{t("registeredAt")}</dt>
                  <dd className="font-medium text-ink">
                    {new Date(me.created_at).toLocaleDateString(
                      locale === "zh" ? "zh-CN" : "en-US",
                    )}
                  </dd>
                </div>
              )}
            </dl>
          ) : (
            <p className="mt-3 text-sm text-soft">{t("loading")}</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
