import Link from "next/link";

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
  try {
    const response = await getActionItems();
    return (
      <AppShell
        currentPath="/actions"
        title="把评论洞察转成团队行动。"
        description="承接 Top 问题、Listing 线索和竞品机会，并推进负责人、状态和复盘。"
      >
        <ActionCenterPanel items={response.items} />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/actions"
          title="行动中心需要先登录。"
          description="登录后可以直接看到当前账号下由评论洞察生成的行动事项和状态。"
        >
          <EmptyAuthState
            title="登录后查看行动中心"
            description="这里会承接增长分析页创建的事项，并继续推进到复盘追踪。"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
