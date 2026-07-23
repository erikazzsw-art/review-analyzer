import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { ActionCenterPanel } from "@/components/actions/action-center-panel";
import { getActionItems, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Action Center",
  description: "Authenticated team action tracking from review insights.",
});

export default async function ActionsPage() {
  const t = await getTranslations("actions.page");

  try {
    const response = await getActionItems();
    return (
      <AppShell
        currentPath="/actions"
        title={t("title")}
        description={t("description")}
      >
        <ActionCenterPanel items={response.items} />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/actions"
          title={t("authTitle")}
          description={t("authDescription")}
        >
          <EmptyAuthState
            title={t("authEmptyTitle")}
            description={t("authEmptyDescription")}
          />
        </AppShell>
      );
    }

    throw error;
  }
}
