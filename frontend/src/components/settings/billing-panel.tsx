"use client";

import { useRef, useState } from "react";

import { createBillingCheckout } from "@/lib/api/browser";
import { Button } from "@/components/ui/button";

type Props = { billing: { plan?: string; configured?: boolean; [key: string]: unknown } };

export function BillingPanel({ billing }: Props) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const checkoutRef = useRef<HTMLDivElement | null>(null);

  const configured = Boolean(billing.configured);

  async function handleCheckout() {
    setError(""); setMessage(""); setIsLoading(true);
    try {
      const result = await createBillingCheckout();
      if (!result.checkout_html) {
        setMessage(result.configured ? "Paddle 已配置，但未返回 checkout 内容。" : "Paddle 还未完全配置，请先检查环境变量。");
        return;
      }
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
      setMessage("Paddle checkout 已打开。");
    } catch (err) {
      setError((err as { message?: string }).message || "发起升级失败");
    } finally { setIsLoading(false); }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card">
        <h2 className="font-heading text-2xl font-extrabold tracking-tight text-ink">订阅计费</h2>
        <p className="mt-1 text-sm text-soft">当前计划：{billing.plan || "Free"}</p>
        <div ref={checkoutRef} className="hidden" aria-hidden="true" />
        <div className="mt-5 flex items-center gap-4">
          <Button type="button" onClick={handleCheckout} disabled={isLoading} className="rounded-pill bg-rose px-5 py-2.5 text-sm font-semibold text-white shadow-card hover:bg-rose/90">
            {isLoading ? "拉起支付..." : configured ? "管理订阅" : "升级到 Pro"}
          </Button>
          {error && <span className="text-sm text-red-600">{error}</span>}
          {message && <span className="text-sm text-green-700">{message}</span>}
        </div>
      </section>
    </div>
  );
}
