import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { PushSettingsPanel } from "@/components/settings/push-settings-panel";
import { getSettings, isApiError } from "@/lib/api/server";

export default async function PushSettingsPage() {
  try {
    const settings = await getSettings();

    return (
      <AppShell currentPath="/settings" title="绑定飞书" description="配置飞书 Webhook 和自动推送规则。">
        <PushSettingsPanel initialSettings={settings} />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell currentPath="/settings" title="绑定飞书" description="登录后配置推送。">
          <EmptyAuthState title="登录后查看推送设置" description="这里管理通知渠道和自动推送规则。" />
        </AppShell>
      );
    }
    throw error;
  }
}
