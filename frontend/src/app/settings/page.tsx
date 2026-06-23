import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { QuotaPanel } from "@/components/settings/quota-panel";
import { SettingsPanel } from "@/components/settings/settings-panel";
import { SmartPushSettingsPanel } from "@/components/settings/smart-push-settings";
import { getQuota, getSettings, isApiError, type QuotaItem } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Notification Settings | ClueAI",
  description: "Authenticated settings for integrations, notifications, and billing.",
});

export default async function SettingsPage() {
  try {
    const settings = await getSettings();
    let quota: QuotaItem[] = [];
    try {
      quota = await getQuota();
    } catch {}

    return (
      <AppShell
        currentPath="/settings"
        title="推送设置集中管理 Webhook、规则和 API Key。"
        description="设置页承接飞书通知、DeepSeek 密钥和 Paddle 升级入口，适合低频调整但不能缺席的系统能力。"
      >
        {quota.length > 0 && <QuotaPanel items={quota} />}
        <SettingsPanel initialSettings={settings} />
        <div className="mt-8 border-t pt-8">
          <SmartPushSettingsPanel />
        </div>
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/settings"
          title="推送设置需要先登录。"
          description="登录后可以直接修改飞书 Webhook、自动推送规则和 API Key。"
        >
          <EmptyAuthState
            title="登录后查看推送设置"
            description="这里会管理通知渠道、自动推送规则和升级入口。"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
