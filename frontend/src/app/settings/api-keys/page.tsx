"use client";

import { useEffect, useState } from "react";

import { fetchSettings } from "@/lib/api/browser";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { ApiKeysPanel } from "@/components/settings/api-keys-panel";

export default function ApiKeysPage() {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unauthorized, setUnauthorized] = useState(false);

  useEffect(() => {
    fetchSettings()
      .then((s) => setApiKey(s.api_key ?? ""))
      .catch((err) => {
        if (err?.status === 401) {
          setUnauthorized(true);
        } else {
          setError(err?.message || "加载设置失败");
        }
      });
  }, []);

  if (unauthorized) {
    return <EmptyAuthState title="登录后管理 API 密钥" description="这里配置 DeepSeek API Key。" />;
  }

  if (error) {
    return (
      <div className="rounded-shell border border-line bg-white/84 p-6 text-center">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (apiKey === null) {
    return (
      <div className="rounded-shell border border-line bg-white/84 p-6 text-center">
        <p className="text-sm text-soft">加载中...</p>
      </div>
    );
  }

  return <ApiKeysPanel initialApiKey={apiKey} />;
}
