"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { openBillingCheckout } from "@/lib/billing";
import { Button } from "@/components/ui/button";

type Props = { billing: { plan?: string; configured?: boolean; [key: string]: unknown } };

export function BillingPanel({ billing }: Props) {
  const t = useTranslations("settings.billing");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const checkoutRef = useRef<HTMLDivElement | null>(null);

  const configured = Boolean(billing.configured);

  async function handleCheckout() {
    setError(""); setMessage(""); setIsLoading(true);
    try {
      const result = await openBillingCheckout(checkoutRef.current);
      if (!result.hasHtml) {
        setMessage(result.configured ? t("notReturned") : t("notConfigured"));
        return;
      }
      setMessage(t("checkoutOpened"));
    } catch (err) {
      setError((err as { message?: string }).message || t("checkoutFail"));
    } finally { setIsLoading(false); }
  }

  return (
    <div>
      <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
        <h2 className="text-base font-bold text-ink">{t("sectionTitle")}</h2>
        <p className="mt-1 text-sm text-soft">{t("currentPlanPrefix", { plan: billing.plan || "Free" })}</p>
        <div ref={checkoutRef} className="hidden" aria-hidden="true" />
        <div className="mt-5 flex items-center gap-4">
          <Button type="button" onClick={handleCheckout} disabled={isLoading} className="rounded-pill bg-rose px-5 py-2.5 text-sm font-semibold text-white shadow-card hover:bg-rose/90">
            {isLoading ? t("loading") : configured ? t("manage") : t("upgrade")}
          </Button>
          {error && <span className="text-sm text-red-600">{error}</span>}
          {message && <span className="text-sm text-green-700">{message}</span>}
        </div>
      </section>
    </div>
  );
}
