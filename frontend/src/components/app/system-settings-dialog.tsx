"use client";

import { useEffect, useState } from "react";

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
  const [me, setMe] = useState<MeData | null>(null);

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
          <DialogTitle className="text-lg font-bold text-ink">系统设置</DialogTitle>
        </DialogHeader>

        <div className="mt-4">
          <h3 className="text-sm font-semibold text-ink">账户信息</h3>
          {me ? (
            <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-soft">用户名</dt>
                <dd className="font-medium text-ink">{me.username}</dd>
              </div>
              {me.email && (
                <div>
                  <dt className="text-soft">邮箱</dt>
                  <dd className="font-medium text-ink">{me.email}</dd>
                </div>
              )}
              <div>
                <dt className="text-soft">当前套餐</dt>
                <dd className="font-medium text-ink">{me.plan === "pro" ? "Pro" : "Free"}</dd>
              </div>
              {me.created_at && (
                <div>
                  <dt className="text-soft">注册时间</dt>
                  <dd className="font-medium text-ink">
                    {new Date(me.created_at).toLocaleDateString("zh-CN")}
                  </dd>
                </div>
              )}
            </dl>
          ) : (
            <p className="mt-3 text-sm text-soft">加载中...</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
