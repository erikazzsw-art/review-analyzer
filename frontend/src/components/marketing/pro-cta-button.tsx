"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { createBillingCheckout } from "@/lib/api/browser";

type Props = {
  label?: string;
  className?: string;
};

export function ProCtaButton({ label = "升级到 Pro", className }: Props) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const checkoutRef = useRef<HTMLDivElement | null>(null);

  async function handleClick() {
    setIsLoading(true);
    try {
      const result = await createBillingCheckout();
      if (!result.checkout_html) return;
      if (checkoutRef.current) {
        checkoutRef.current.innerHTML = result.checkout_html;
        const scripts = Array.from(checkoutRef.current.querySelectorAll("script"));
        for (const script of scripts) {
          await new Promise<void>((resolve, reject) => {
            const next = document.createElement("script");
            Array.from(script.attributes).forEach((attr) => next.setAttribute(attr.name, attr.value));
            if (next.src) { next.onload = () => resolve(); next.onerror = () => reject(new Error("加载脚本失败")); }
            else { next.text = script.textContent || ""; resolve(); }
            script.replaceWith(next);
          });
        }
      }
    } catch (err: unknown) {
      const status = (err as { status?: number }).status;
      if (status === 401) {
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
        {isLoading ? "处理中..." : label}
      </button>
      <div ref={checkoutRef} className="hidden" aria-hidden="true" />
    </>
  );
}
