"use client";

import { useEffect, useState } from "react";

import { fetchSettings } from "@/lib/api/browser";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { ApiKeysPanel } from "@/components/settings/api-keys-panel";

type MeData = { username: string; email?: string; plan: string; created_at?: string };

export default function SystemSettingsPage() {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [me, setMe] = useState<MeData | null>(null);
  const [unauthorized, setUnauthorized] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSettings()
      .then((s) => setApiKey(s.api_key ?? ""))
      .catch((err) => {
        if (err?.status === 401) setUnauthorized(true);
        else setError(err?.message || "加载设置失败");
      });

    fetch("/api/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setMe(d as MeData); })
      .catch(() => {});
  }, []);

  if (unauthorized) {
    return (
      <div className="px-6 pt-6 lg:px-10">
        <EmptyAuthState title="登录后访问系统设置" description="管理 API 密钥和账户信息。" />
      </div>
    );
  }

  return (
    <div className="px-6 pt-6 lg:px-10">
      <header className="pb-5">
        <h1 className="font-heading text-2xl font-extrabold tracking-[-0.03em] text-ink md:text-3xl">
          系统设置
        </h1>
        <p className="mt-1.5 text-sm leading-6 text-soft md:text-base">
          管理 API 密钥和账户信息。
        </p>
      </header>

      <div className="space-y-5">
        {/* 账户信息 */}
        <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
          <h2 className="text-base font-bold text-ink">账户信息</h2>
          {me ? (
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
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
                  <dd className="font-medium text-ink">{new Date(me.created_at).toLocaleDateString("zh-CN")}</dd>
                </div>
              )}
            </dl>
          ) : (
            <p className="mt-3 text-sm text-soft">加载中...</p>
          )}
        </section>

        {/* API 密钥 */}
        {error ? (
          <div className="rounded-shell border border-line bg-white/84 p-6 text-center">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        ) : apiKey === null ? (
          <div className="rounded-shell border border-line bg-white/84 p-6 text-center">
            <p className="text-sm text-soft">加载中...</p>
          </div>
        ) : (
          <ApiKeysPanel initialApiKey={apiKey} />
        )}

        {/* 占位功能 */}
        <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card">
          <h2 className="text-base font-bold text-ink">数据导出</h2>
          <p className="mt-1 text-sm text-soft">导出所有分析数据和评论记录。</p>
          <div className="mt-4">
            <button disabled className="rounded-pill border border-line bg-muted px-5 py-2 text-sm font-medium text-soft cursor-not-allowed">
              即将上线
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
