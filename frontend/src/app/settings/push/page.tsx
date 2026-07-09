"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { fetchSettings } from "@/lib/api/browser";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { PushSettingsPanel } from "@/components/settings/push-settings-panel";
import type { SettingsResponse } from "@/lib/api/types";

export default function PushSettingsPage() {
  const t = useTranslations("settings.layout");
  const tCommon = useTranslations("settings.common");
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unauthorized, setUnauthorized] = useState(false);

  useEffect(() => {
    fetchSettings()
      .then(setSettings)
      .catch((err) => {
        if (err?.status === 401) {
          setUnauthorized(true);
        } else {
          setError(err?.message || t("pageLoadError"));
        }
      });
  }, [t]);

  if (unauthorized) {
    return <EmptyAuthState title={t("unauthorizedTitle")} description={t("unauthorizedDesc")} />;
  }

  if (error) {
    return (
      <div className="rounded-shell border border-line bg-white/84 p-6 text-center">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="rounded-shell border border-line bg-white/84 p-6 text-center">
        <p className="text-sm text-soft">{tCommon("loading")}</p>
      </div>
    );
  }

  return <PushSettingsPanel initialSettings={settings} />;
}
