"use client";

import { useEffect, useState } from "react";

import { fetchSettings } from "@/lib/api/browser";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { BillingPanel } from "@/components/settings/billing-panel";

export default function BillingPage() {
  const [billing, setBilling] = useState<{ plan?: string; configured?: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unauthorized, setUnauthorized] = useState(false);

  useEffect(() => {
    fetchSettings()
      .then((s) => setBilling(s.billing ?? { plan: "Free" }))
      .catch((err) => {
        if (err?.status === 401) {
          setUnauthorized(true);
        } else {
          setError(err?.message || "加载设置失败");
        }
      });
  }, []);

  if (unauthorized) {
    return <EmptyAuthState title="登录后管理订阅" description="这里查看和升级订阅计划。" />;
  }

  if (error) {
    return (
      <div className="rounded-shell border border-line bg-white/84 p-6 text-center">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!billing) {
    return (
      <div className="rounded-shell border border-line bg-white/84 p-6 text-center">
        <p className="text-sm text-soft">加载中...</p>
      </div>
    );
  }

  return <BillingPanel billing={billing} />;
}
