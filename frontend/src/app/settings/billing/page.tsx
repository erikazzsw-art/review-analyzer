import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { BillingPanel } from "@/components/settings/billing-panel";
import { getSettings, isApiError } from "@/lib/api/server";

export default async function BillingPage() {
  try {
    const settings = await getSettings();

    return (
      <AppShell currentPath="/settings" title="订阅计费" description="管理订阅计划。">
        <BillingPanel billing={settings.billing} />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell currentPath="/settings" title="订阅计费" description="登录后管理。">
          <EmptyAuthState title="登录后管理订阅" description="这里查看和升级订阅计划。" />
        </AppShell>
      );
    }
    throw error;
  }
}
