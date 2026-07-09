"use client";

import { Coins } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import type { QuotaItem } from "@/lib/api/server";
import { QuotaDialog } from "@/components/quota/quota-dialog";
import type { PlanKey } from "@/lib/pricing";

import { CreditLedgerDrawer } from "./credit-ledger-drawer";
import { UpgradePricingDialog } from "./upgrade-pricing-dialog";

interface CreditBalance {
  balance: number;
  monthly_grant: number;
  trial_expires_at: string | null;
  days_left: number | null;
  is_trial: boolean;
}

function derivePlan(monthlyGrant: number): PlanKey {
  if (monthlyGrant >= 45000) return "team";
  if (monthlyGrant >= 15000) return "pro";
  if (monthlyGrant >= 5000) return "starter";
  return "free";
}

export function SidebarCreditEntry() {
  const t = useTranslations("credit.sidebar");
  const [quotaOpen, setQuotaOpen] = useState(false);
  const [ledgerOpen, setLedgerOpen] = useState(false);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [data, setData] = useState<CreditBalance | null>(null);
  const [quotaItems, setQuotaItems] = useState<QuotaItem[] | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/credits/balance", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: CreditBalance | null) => {
        if (active && d) setData(d);
      })
      .catch(() => {});
    fetch("/api/quota", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((items) => {
        if (active && Array.isArray(items)) {
          setQuotaItems(items as QuotaItem[]);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const currentPlan: PlanKey = data ? derivePlan(data.monthly_grant) : "free";
  const showUpgrade = currentPlan !== "team";

  return (
    <>
      <div className="mb-3 flex items-stretch gap-2 rounded-card border border-line bg-white/70 px-3 py-2 transition hover:bg-roseSoft/40">
        <button
          type="button"
          onClick={() => setQuotaOpen(true)}
          className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
          aria-label={t("creditsLabel")}
        >
          <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-600">
            <Coins size={15} />
          </span>
          <span className="flex min-w-0 flex-col">
            <span className="truncate text-xs font-semibold text-ink">{t("creditsLabel")}</span>
            {data ? (
              <span className="truncate text-[11px] text-soft">
                {data.balance.toLocaleString()}
                {data.is_trial && data.days_left !== null
                  ? ` · ${t("trialDaysLeft", { days: data.days_left })}`
                  : ` / ${data.monthly_grant.toLocaleString()}`}
              </span>
            ) : (
              <span className="h-3 w-16 animate-pulse rounded bg-line" />
            )}
          </span>
        </button>
        {showUpgrade && (
          <button
            type="button"
            onClick={() => setUpgradeOpen(true)}
            className="self-center whitespace-nowrap text-xs font-semibold text-rose hover:underline"
          >
            {t("upgradeButton")}
          </button>
        )}
      </div>

      {quotaItems && (
        <QuotaDialog
          open={quotaOpen}
          onOpenChange={setQuotaOpen}
          items={quotaItems}
        />
      )}

      <UpgradePricingDialog
        open={upgradeOpen}
        onOpenChange={setUpgradeOpen}
        currentPlan={currentPlan}
        onOpenLedger={() => {
          setUpgradeOpen(false);
          setLedgerOpen(true);
        }}
      />

      <CreditLedgerDrawer open={ledgerOpen} onOpenChange={setLedgerOpen} />
    </>
  );
}
