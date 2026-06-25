import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { ApiKeysPanel } from "@/components/settings/api-keys-panel";
import { getSettings, isApiError } from "@/lib/api/server";

export default async function ApiKeysPage() {
  try {
    const settings = await getSettings();

    return (
      <AppShell currentPath="/settings" title="API 密钥" description="管理 DeepSeek API Key。">
        <ApiKeysPanel initialApiKey={settings.api_key} />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell currentPath="/settings" title="API 密钥" description="登录后管理。">
          <EmptyAuthState title="登录后管理 API 密钥" description="这里配置 DeepSeek API Key。" />
        </AppShell>
      );
    }
    throw error;
  }
}
