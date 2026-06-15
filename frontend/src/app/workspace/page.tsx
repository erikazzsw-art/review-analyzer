import Link from "next/link";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { getWorkspaceSummary, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";
import type { WorkspaceRole } from "@/lib/api/types";

export const metadata = buildNoIndexMetadata({
  title: "Today's Workspace | ClueAI",
  description: "Authenticated workspace for review operations and follow-up tracking.",
});

const roleLabels: Record<WorkspaceRole, string> = {
  "运营": "运营",
  "产研": "产研",
  "质检": "质检",
  "管理者": "管理者",
};

const roleList: WorkspaceRole[] = ["运营", "产研", "质检", "管理者"];

function taskHref(page: string): string {
  if (page === "products") {
    return "/products";
  }
  if (page === "actions") {
    return "/actions";
  }
  if (page === "reviews") {
    return "/reviews";
  }
  if (page === "analysis") {
    return "/analysis/results";
  }
  if (page === "rag") {
    return "/qa";
  }
  return "/workspace";
}

type WorkspacePageProps = {
  searchParams?: Promise<{
    role?: string;
  }>;
};

export default async function WorkspacePage({
  searchParams,
}: WorkspacePageProps) {
  const params = searchParams ? await searchParams : undefined;
  const rawRole = params?.role;
  const selectedRole = roleList.includes(rawRole as WorkspaceRole)
    ? (rawRole as WorkspaceRole)
    : "运营";

  try {
    const summary = await getWorkspaceSummary(selectedRole);
    return (
      <AppShell
        currentPath="/workspace"
        title="今日工作台"
        description="风险 SKU、团队待办、待复盘事项和最近上传，一个经营视角看全局"
      >
        <section className="rounded-shell border border-line bg-card px-6 py-6 shadow-card backdrop-blur md:px-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
                TODAY&apos;S WORKSPACE
              </div>
              <h2 className="mt-5 max-w-3xl font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink md:text-[2.6rem]">
                {summary.intro.headline}
              </h2>
              <p className="mt-3 max-w-2xl text-base leading-8 text-soft">
                {summary.intro.focus}
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {roleList.map((role) => {
                const isActive = role === summary.role;
                return (
                  <Link
                    key={role}
                    href={`/workspace?role=${encodeURIComponent(role)}`}
                    className={[
                      "inline-flex min-h-11 items-center justify-center rounded-pill border px-4 py-2 text-sm font-semibold transition",
                      isActive
                        ? "border-transparent bg-ink text-white shadow-card"
                        : "border-line bg-white/80 text-soft hover:bg-white hover:text-ink",
                    ].join(" ")}
                  >
                    {roleLabels[role]}
                  </Link>
                );
              })}
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              产品组
            </div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {summary.metrics.product_count}
            </div>
          </div>
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              高风险 SKU
            </div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-[#d94d72]">
              {summary.metrics.risk_product_count}
            </div>
          </div>
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              未完结事项
            </div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {summary.metrics.open_action_count}
            </div>
          </div>
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              待复盘
            </div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {summary.metrics.open_tracker_count}
            </div>
          </div>
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
              7 天上传
            </div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {summary.metrics.recent_upload_count}
            </div>
          </div>
        </section>

        <section className="rounded-shell border border-line bg-white/82 p-6 shadow-card backdrop-blur">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                今日最该处理的 1-3 件事
              </h3>
            </div>
          </div>

          <div className="mt-5 grid gap-4">
            {summary.today_tasks.length > 0 ? (
              summary.today_tasks.map((task) => (
                <div
                  key={`${task.category}-${task.title}`}
                  className="rounded-card border border-line bg-white px-5 py-5"
                >
                  <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                    {task.category}
                  </div>
                  <div className="mt-3 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                    {task.title}
                  </div>
                  <p className="mt-3 max-w-3xl text-sm leading-7 text-soft">
                    {task.description}
                  </p>
                  <Link
                    href={taskHref(task.page)}
                    className="mt-5 inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
                  >
                    {task.cta_label}
                  </Link>
                </div>
              ))
            ) : (
              <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-5 py-6 text-sm leading-7 text-soft">
                当前还没有足够数据生成待办，先上传评论或创建行动事项。
              </div>
            )}
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
          <div className="space-y-6">
            <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
              <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                高风险 SKU
              </h3>
              <div className="mt-5 space-y-3">
                {summary.risk_products.length > 0 ? (
                  summary.risk_products.map((item) => (
                    <div
                      key={`${item.product_id ?? item.product_name}-${item.top_issue}`}
                      className="rounded-card border border-line bg-[#fff8f9] px-5 py-5"
                    >
                      <div className="text-lg font-semibold text-ink">
                        {item.product_name}
                      </div>
                      <div className="mt-2 text-sm leading-7 text-soft">
                        差评率 {item.negative_rate.toFixed(1)}% · {item.review_count} 条评论
                      </div>
                      <div className="mt-1 text-sm leading-7 text-soft">
                        核心问题：{item.top_issue} · 待复盘 {item.pending_review_count} 项
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-card border border-dashed border-line bg-white px-5 py-6 text-sm leading-7 text-soft">
                    当前没有明显高风险 SKU，适合继续做常规监控。
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
              <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                最近上传
              </h3>
              <div className="mt-5 space-y-3">
                {summary.recent_sessions.length > 0 ? (
                  summary.recent_sessions.map((item) => (
                    <div
                      key={item.session_id}
                      className="rounded-card border border-line bg-white px-5 py-5"
                    >
                      <div className="text-base font-semibold text-ink">
                        {item.title}
                      </div>
                      <div className="mt-2 text-sm leading-7 text-soft">
                        {item.product_id} · {item.workflow_purpose}
                      </div>
                      <div className="mt-1 text-sm leading-7 text-soft">
                        {item.created_at} · {item.total_reviews} 条评论
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-card border border-dashed border-line bg-white px-5 py-6 text-sm leading-7 text-soft">
                    最近还没有新的上传批次。
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
              <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                待复盘事项
              </h3>
              <div className="mt-5 space-y-3">
                {summary.pending_trackers.length > 0 ? (
                  summary.pending_trackers.map((item) => (
                    <div
                      key={`${item.title}-${item.tag_name}`}
                      className="rounded-card border border-line bg-[#fbf9ff] px-5 py-5"
                    >
                      <div className="text-base font-semibold text-ink">
                        {item.title}
                      </div>
                      <div className="mt-2 text-sm leading-7 text-soft">
                        {item.product_name} · {item.tag_name} · {item.status}
                      </div>
                      <div className="mt-1 text-sm leading-7 text-soft">
                        初始占比{" "}
                        {item.baseline_pct === null
                          ? "—"
                          : `${item.baseline_pct.toFixed(1)}%`}{" "}
                        → 当前占比{" "}
                        {item.current_pct === null
                          ? "—"
                          : `${item.current_pct.toFixed(1)}%`}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-card border border-dashed border-line bg-white px-5 py-6 text-sm leading-7 text-soft">
                    当前没有待复盘事项，团队动作相对干净。
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
              <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                角色事项分布
              </h3>
              <div className="mt-5 space-y-3">
                {summary.role_action_summary.map((item) => (
                  <div
                    key={item.role}
                    className="flex items-center justify-between rounded-card border border-line bg-white px-5 py-4"
                  >
                    <span className="text-sm font-semibold text-ink">
                      {item.role}
                    </span>
                    <span className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                      {item.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/workspace"
          title="请先登录"
          description="登录后即可查看风险 SKU、团队待办和最近上传"
        >
          <EmptyAuthState
            title="登录后查看风险 SKU、团队待办和最近上传"
            description="登录后系统会自动加载你的工作台数据"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
