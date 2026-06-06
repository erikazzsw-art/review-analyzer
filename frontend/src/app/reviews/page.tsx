import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { ReviewTrackerPanel } from "@/components/reviews/review-tracker-panel";
import { getReviewTrackers, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Follow-up Tracking | ClueAI",
  description: "Authenticated follow-up validation and review tracking.",
});

export default async function ReviewsPage() {
  try {
    const response = await getReviewTrackers();
    return (
      <AppShell
        currentPath="/reviews"
        title="复盘追踪把改进前后结果继续落下来。"
        description="这里记录当前占比、复盘范围、结论状态和最终判断。"
      >
        <ReviewTrackerPanel items={response.items} />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/reviews"
          title="复盘追踪需要先登录。"
          description="登录后会直接读取当前账号下的 tracker 数据。"
        >
          <EmptyAuthState
            title="登录后查看复盘追踪"
            description="这条能力会记录改进前后占比和结论，方便判断动作是否真的有效。"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
