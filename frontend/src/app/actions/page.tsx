import Link from "next/link";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { ActionCenterPanel } from "@/components/actions/action-center-panel";
import { getActionItems, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Action Center | ClueAI",
  description: "Authenticated action tracking and ownership handoff.",
});

export default async function ActionsPage() {
  try {
    const response = await getActionItems();
    return (
      <AppShell
        currentPath="/actions"
        title="把 TOP 问题转成行动事项，再持续推进状态。"
        description="行动中心承接分析结果页创建的事项，并支持加入复盘追踪。"
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
          description="登录后可以直接看到当前账号下的行动事项和状态。"
        >
          <EmptyAuthState
            title="登录后查看行动中心"
            description="这里会承接分析结果页创建的事项，并继续推进到复盘追踪。"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
