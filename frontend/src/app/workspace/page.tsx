import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { getWorkspaceSummary, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";
import type { WorkspaceRole, WorkspaceSummary } from "@/lib/api/types";

export const metadata = buildNoIndexMetadata({
  title: "Today's Workspace | ClueAI",
  description: "Authenticated workspace for review operations and follow-up tracking.",
});

const roleLabelKeys: Record<WorkspaceRole, string> = {
  "运营": "roleOps",
  "产研": "roleProduct",
  "质检": "roleQA",
  "管理者": "roleManager",
};

const roleList: WorkspaceRole[] = ["运营", "产研", "质检", "管理者"];

function taskHref(page: string): string {
  if (page === "products") return "/products";
  if (page === "actions") return "/actions";
  if (page === "reviews") return "/reviews";
  if (page === "analysis") return "/analysis/results";
  if (page === "rag") return "/qa";
  return "/workspace";
}

function safeText(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function safeNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function safeNullNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeSummary(summary: WorkspaceSummary): WorkspaceSummary {
  return {
    ...summary,
    role: roleList.includes(summary.role) ? summary.role : "运营",
    intro: {
      headline: safeText(summary.intro?.headline, "欢迎回来"),
      focus: safeText(summary.intro?.focus, "工作台数据正在加载。"),
    },
    metrics: {
      product_count: safeNumber(summary.metrics?.product_count),
      risk_product_count: safeNumber(summary.metrics?.risk_product_count),
      open_action_count: safeNumber(summary.metrics?.open_action_count),
      open_tracker_count: safeNumber(summary.metrics?.open_tracker_count),
      recent_upload_count: safeNumber(summary.metrics?.recent_upload_count),
    },
    today_tasks: Array.isArray(summary.today_tasks)
      ? summary.today_tasks.map((task) => ({
          category: safeText(task?.category, "未分类"),
          title: safeText(task?.title, "待处理事项"),
          description: safeText(task?.description, "暂无描述。"),
          cta_label: safeText(task?.cta_label, "继续处理"),
          page: safeText(task?.page, "/workspace"),
          session_updates:
            task?.session_updates && typeof task.session_updates === "object"
              ? task.session_updates
              : {},
        }))
      : [],
    risk_products: Array.isArray(summary.risk_products)
      ? summary.risk_products.map((item) => ({
          product_id: item?.product_id ?? null,
          product_name: safeText(item?.product_name, "未命名产品"),
          negative_rate: safeNumber(item?.negative_rate),
          top_issue: safeText(item?.top_issue, "暂无问题"),
          pending_review_count: safeNumber(item?.pending_review_count),
          review_count: safeNumber(item?.review_count),
          latest_session_label: safeText(item?.latest_session_label, "最近批次"),
        }))
      : [],
    pending_trackers: Array.isArray(summary.pending_trackers)
      ? summary.pending_trackers.map((item) => ({
          title: safeText(item?.title, "待复盘事项"),
          product_name: safeText(item?.product_name, "未命名产品"),
          tag_name: safeText(item?.tag_name, "未分类"),
          status: safeText(item?.status, "new"),
          baseline_pct: safeNullNumber(item?.baseline_pct),
          current_pct: safeNullNumber(item?.current_pct),
          review_scope: safeText(item?.review_scope, "all"),
        }))
      : [],
    role_action_summary: Array.isArray(summary.role_action_summary)
      ? summary.role_action_summary.map((item) => ({
          role: safeText(item?.role, "未知"),
          count: safeNumber(item?.count),
        }))
      : [],
    recent_sessions: Array.isArray(summary.recent_sessions)
      ? summary.recent_sessions.map((item) => ({
          session_id: safeNumber(item?.session_id),
          title: safeText(item?.title, "未命名批次"),
          product_id: safeText(item?.product_id, ""),
          workflow_purpose: safeText(item?.workflow_purpose, "manual"),
          created_at: safeText(item?.created_at, ""),
          total_reviews: safeNumber(item?.total_reviews),
        }))
      : [],
    generated_at: summary.generated_at,
  };
}

type WorkspacePageProps = {
  searchParams?: Promise<{
    role?: string;
  }>;
};

export default async function WorkspacePage({ searchParams }: WorkspacePageProps) {
  const t = await getTranslations("workspace");
  const params = searchParams ? await searchParams : undefined;
  const rawRole = params?.role;
  const selectedRole = roleList.includes(rawRole as WorkspaceRole)
    ? (rawRole as WorkspaceRole)
    : "运营";

  try {
    const summary = normalizeSummary(await getWorkspaceSummary(selectedRole));
    return (
      <AppShell
        currentPath="/workspace"
        title={t("title")}
        description={t("description")}
      >
        <section className="rounded-shell border border-line bg-card px-6 py-6 shadow-card backdrop-blur md:px-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
                {t("badge")}
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
                    {t(roleLabelKeys[role])}
                  </Link>
                );
              })}
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("metricProducts")}</div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {summary.metrics.product_count}
            </div>
          </div>
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("metricRisk")}</div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-[#d94d72]">
              {summary.metrics.risk_product_count}
            </div>
          </div>
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("metricOpenActions")}</div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {summary.metrics.open_action_count}
            </div>
          </div>
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("metricPendingReview")}</div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {summary.metrics.open_tracker_count}
            </div>
          </div>
          <div className="rounded-card border border-line bg-white/82 px-5 py-5 shadow-card backdrop-blur">
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("metricRecentUploads")}</div>
            <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
              {summary.metrics.recent_upload_count}
            </div>
          </div>
        </section>

        <section className="rounded-shell border border-line bg-white/82 p-6 shadow-card backdrop-blur">
          <div className="flex items-center justify-between gap-4">
            <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              {t("todayTasks")}
            </h3>
          </div>

          <div className="mt-5 grid gap-4">
            {summary.today_tasks.length > 0 ? (
              summary.today_tasks.map((task) => (
                <div
                  key={`${task.category}-${task.title}`}
                  className="rounded-card border border-line bg-white px-5 py-5"
                >
                  <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{task.category}</div>
                  <div className="mt-3 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                    {task.title}
                  </div>
                  <p className="mt-3 max-w-3xl text-sm leading-7 text-soft">{task.description}</p>
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
                {t("todayTasksEmpty")}
              </div>
            )}
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
          <div className="space-y-6">
            <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
              <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">{t("riskProducts")}</h3>
              <div className="mt-5 space-y-3">
                {summary.risk_products.length > 0 ? (
                  summary.risk_products.map((item) => (
                    <div
                      key={`${item.product_id ?? item.product_name}-${item.top_issue}`}
                      className="rounded-card border border-line bg-[#fff8f9] px-5 py-5"
                    >
                      <div className="text-lg font-semibold text-ink">{item.product_name}</div>
                      <div className="mt-2 text-sm leading-7 text-soft">
                        {t("riskNegativeRate")} {item.negative_rate.toFixed(1)}% · {item.review_count} {t("riskReviews")}
                      </div>
                      <div className="mt-1 text-sm leading-7 text-soft">
                        {t("riskCoreIssue")}：{item.top_issue} · {t("riskPendingReview")} {item.pending_review_count} {t("riskItems")}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-card border border-dashed border-line bg-white px-5 py-6 text-sm leading-7 text-soft">
                    {t("riskProductsEmpty")}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
              <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">{t("recentUploads")}</h3>
              <div className="mt-5 space-y-3">
                {summary.recent_sessions.length > 0 ? (
                  summary.recent_sessions.map((item) => (
                    <div
                      key={item.session_id}
                      className="rounded-card border border-line bg-white px-5 py-5"
                    >
                      <div className="text-base font-semibold text-ink">{item.title}</div>
                      <div className="mt-2 text-sm leading-7 text-soft">
                        {item.product_id} · {item.workflow_purpose}
                      </div>
                      <div className="mt-1 text-sm leading-7 text-soft">
                        {item.created_at} · {item.total_reviews} {t("riskReviews")}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-card border border-dashed border-line bg-white px-5 py-6 text-sm leading-7 text-soft">
                    {t("recentUploadsEmpty")}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
              <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">{t("pendingTrackers")}</h3>
              <div className="mt-5 space-y-3">
                {summary.pending_trackers.length > 0 ? (
                  summary.pending_trackers.map((item) => (
                    <div
                      key={`${item.title}-${item.tag_name}`}
                      className="rounded-card border border-line bg-[#fbf9ff] px-5 py-5"
                    >
                      <div className="text-base font-semibold text-ink">{item.title}</div>
                      <div className="mt-2 text-sm leading-7 text-soft">
                        {item.product_name} · {item.tag_name} · {item.status}
                      </div>
                      <div className="mt-1 text-sm leading-7 text-soft">
                        {item.baseline_pct === null ? "—" : `${item.baseline_pct.toFixed(1)}%`} → {item.current_pct === null ? "—" : `${item.current_pct.toFixed(1)}%`}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-card border border-dashed border-line bg-white px-5 py-6 text-sm leading-7 text-soft">
                    {t("pendingTrackersEmpty")}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
              <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">{t("roleActions")}</h3>
              <div className="mt-5 space-y-3">
                {summary.role_action_summary.length > 0 ? (
                  summary.role_action_summary.map((item) => (
                    <div
                      key={item.role}
                      className="flex items-center justify-between rounded-card border border-line bg-white px-5 py-4"
                    >
                      <span className="text-sm font-semibold text-ink">{item.role}</span>
                      <span className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                        {item.count}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="rounded-card border border-dashed border-line bg-white px-5 py-6 text-sm leading-7 text-soft">
                    {t("roleActionsEmpty")}
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell currentPath="/workspace" title={t("title")} description={t("description")}>
          <EmptyAuthState
            title={t("title")}
            description={t("description")}
          />
        </AppShell>
      );
    }

    throw error;
  }
}
