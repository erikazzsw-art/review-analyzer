"use client";

import Link from "next/link";
import { Gauge } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import type { QuotaItem } from "@/lib/api/server";
import { PLAN_LABEL_KEY } from "./quota-groups";
import { QuotaDialog } from "./quota-dialog";

export function SidebarQuotaEntry() {
  const tSidebar = useTranslations("sidebar");
  const tDialog = useTranslations("quotaDialog");
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<QuotaItem[] | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let active = true;
    fetch("/api/quota", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!active) return;
        if (Array.isArray(data)) {
          setItems(data as QuotaItem[]);
        } else {
          setLoadFailed(true);
        }
      })
      .catch(() => {
        if (active) setLoadFailed(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const plan = items?.[0]?.plan ?? "free";
  const planLabel = tDialog(PLAN_LABEL_KEY[plan] ?? "plans.free");
  const reviewItem = items?.find((it) => it.dimension === "review_analyze");
  const isFree = plan === "free";

  let preview = "";
  if (items && reviewItem && !reviewItem.error) {
    if (reviewItem.unlimited || reviewItem.limit === -1) {
      preview = `${planLabel} · ${tDialog("unlimited")}`;
    } else {
      preview = `${planLabel} · ${reviewItem.used ?? 0}/${reviewItem.limit}`;
    }
  } else if (!loadFailed && items) {
    preview = planLabel;
  }

  return (
    <>
      <div className="mb-3 flex items-stretch gap-2 rounded-card border border-line bg-white/70 px-3 py-2 transition hover:bg-roseSoft/40">
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
          aria-label={tSidebar("quotaEntry")}
        >
          <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-lavender/10 text-lavender">
            <Gauge size={15} />
          </span>
          <span className="flex min-w-0 flex-col">
            <span className="truncate text-xs font-semibold text-ink">
              {tSidebar("quotaEntry")}
            </span>
            {preview && (
              <span className="truncate text-[11px] text-soft">{preview}</span>
            )}
          </span>
        </button>
        {isFree && (
          <Link
            href="/pricing"
            className="self-center whitespace-nowrap text-xs font-semibold text-rose hover:underline"
          >
            {tSidebar("upgradeLink")}
          </Link>
        )}
      </div>

      {items && (
        <QuotaDialog open={open} onOpenChange={setOpen} items={items} />
      )}
    </>
  );
}
