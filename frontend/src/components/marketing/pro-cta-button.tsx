"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { openBillingCheckout, isUnauthenticatedCheckoutError } from "@/lib/billing";

type Props = {
  label?: string;
  className?: string;
};

export function ProCtaButton({ label, className }: Props) {
  const t = useTranslations("marketing.proCta");
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const checkoutRef = useRef<HTMLDivElement | null>(null);

  async function handleClick() {
    setIsLoading(true);
    try {
      await openBillingCheckout(checkoutRef.current);
    } catch (err: unknown) {
      if (isUnauthenticatedCheckoutError(err)) {
        router.push("/register?plan=pro");
        return;
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        disabled={isLoading}
        className={className}
      >
        {isLoading ? t("loading") : (label ?? t("defaultLabel"))}
      </button>
      <div ref={checkoutRef} className="hidden" aria-hidden="true" />
    </>
  );
}
