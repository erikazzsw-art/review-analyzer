"use client";

import { Coins } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { CreditLedgerDrawer } from "./credit-ledger-drawer";

interface CreditBalance {
  balance: number;
  monthly_grant: number;
  trial_expires_at: string | null;
  days_left: number | null;
  is_trial: boolean;
}

export function SidebarCreditEntry() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<CreditBalance | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/credits/balance", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: CreditBalance | null) => {
        if (active && d) setData(d);
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const pct = data
    ? Math.min(100, Math.round((data.balance / Math.max(data.monthly_grant, 1)) * 100))
    : null;
  const isLow = pct !== null && pct < 20;

  return (
    <>
      <div className="mb-3 flex items-stretch gap-2 rounded-card border border-line bg-white/70 px-3 py-2 transition hover:bg-roseSoft/40">
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex min-w-0 flex-1 items-center gap-2.5 text-left"
          aria-label="Credit balance"
        >
          <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-600">
            <Coins size={15} />
          </span>
          <span className="flex min-w-0 flex-col">
            <span className="truncate text-xs font-semibold text-ink">Credits</span>
            {data ? (
              <span className="truncate text-[11px] text-soft">
                {data.balance.toLocaleString()}
                {data.is_trial && data.days_left !== null
                  ? ` · Trial ${data.days_left}d left`
                  : ` / ${data.monthly_grant.toLocaleString()}`}
              </span>
            ) : (
              <span className="h-3 w-16 animate-pulse rounded bg-line" />
            )}
          </span>
        </button>
        {isLow && (
          <Link
            href="/pricing"
            className="self-center whitespace-nowrap text-xs font-semibold text-rose hover:underline"
          >
            Top up
          </Link>
        )}
      </div>

      <CreditLedgerDrawer open={open} onOpenChange={setOpen} />
    </>
  );
}
