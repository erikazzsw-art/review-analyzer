import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { getWorkspaceSummary, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { WorkspaceSummary } from "@/lib/api/types";

export const metadata = buildNoIndexMetadata({
  title: "Growth Workspace",
  description: "Authenticated workspace for review-driven growth decisions and follow-up tracking.",
});

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
  const responsibilityActionSummary = Array.isArray(summary.responsibility_action_summary)
    ? summary.responsibility_action_summary.map((item) => ({
        responsibility: safeText(item?.responsibility, "未归属"),
        count: safeNumber(item?.count),
      }))
    : Array.isArray(summary.role_action_summary)
      ? summary.role_action_summary.map((item) => ({
          responsibility: safeText(item?.role, "未归属"),
          count: safeNumber(item?.count),
        }))
      : [];

  return {
    ...summary,
    intro: {
      headline: safeText(summary.intro?.headline, "准备查看今日增长信号"),
      focus: safeText(summary.intro?.focus, "导入评论后，这里会汇总风险、机会和团队行动。"),
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
    responsibility_action_summary: responsibilityActionSummary,
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

export default async function WorkspacePage() {
  const t = await getTranslations("workspace");

  try {
    const summary = normalizeSummary(await getWorkspaceSummary());
    const actionOwnershipSummary = summary.responsibility_action_summary ?? [];
    return (
      <AppShell
        currentPath="/workspace"
        title={t("title")}
        description={t("description")}
      >
        {/* Hero */}
        <section className="rounded-shell border border-line bg-card px-5 py-5 shadow-card backdrop-blur">
          <div>
            <h2 className="max-w-3xl font-heading text-2xl font-extrabold tracking-normal text-ink md:text-3xl">
              {summary.intro.headline}
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-soft">
              {summary.intro.focus}
            </p>
          </div>
        </section>

        {/* Metrics — single row with dividers */}
        <section className="flex flex-wrap items-stretch divide-x divide-line rounded-shell border border-line bg-white/82 shadow-card backdrop-blur">
          {[
            { label: t("metricProducts"), value: summary.metrics.product_count, color: "text-ink" },
            { label: t("metricRisk"), value: summary.metrics.risk_product_count, color: "text-[#d94d72]" },
            { label: t("metricOpenActions"), value: summary.metrics.open_action_count, color: "text-ink" },
            { label: t("metricPendingReview"), value: summary.metrics.open_tracker_count, color: "text-ink" },
            { label: t("metricRecentUploads"), value: summary.metrics.recent_upload_count, color: "text-ink" },
          ].map((metric) => (
            <div key={metric.label} className="flex-1 basis-[140px] px-5 py-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{metric.label}</div>
              <div className={`mt-1.5 font-heading text-2xl font-extrabold tracking-normal ${metric.color}`}>
                {metric.value}
              </div>
            </div>
          ))}
        </section>

        {/* Today Tasks — table style */}
        <section className="rounded-shell border border-line bg-white/82 p-5 shadow-card backdrop-blur">
          <h3 className="font-heading text-lg font-extrabold tracking-normal text-ink">
            {t("todayTasks")}
          </h3>
          {summary.today_tasks.length > 0 ? (
            <Table className="mt-3">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-24">类别</TableHead>
                  <TableHead className="min-w-[160px]">任务</TableHead>
                  <TableHead>描述</TableHead>
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.today_tasks.map((task) => (
                  <TableRow key={`${task.category}-${task.title}`}>
                    <TableCell className="text-xs font-semibold uppercase tracking-wide text-soft">
                      {task.category}
                    </TableCell>
                    <TableCell className="text-sm font-semibold text-ink">{task.title}</TableCell>
                    <TableCell className="max-w-sm text-sm leading-6 text-soft">
                      {task.description.length > 80
                        ? task.description.slice(0, 80) + "..."
                        : task.description}
                    </TableCell>
                    <TableCell>
                      <Link
                        href={taskHref(task.page)}
                        className="inline-flex items-center rounded-pill bg-ink px-3 py-1.5 text-xs font-semibold text-white"
                      >
                        {task.cta_label}
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="mt-3 rounded-card border border-dashed border-line bg-[#fffafb] px-5 py-5 text-sm leading-7 text-soft">
              {t("todayTasksEmpty")}
            </div>
          )}
        </section>

        {/* Risk Products + Pending Trackers — side by side */}
        <section className="grid gap-4 xl:grid-cols-[1.12fr_0.88fr]">
          <div className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
            <h3 className="font-heading text-lg font-extrabold tracking-normal text-ink">{t("riskProducts")}</h3>
            {summary.risk_products.length > 0 ? (
              <Table className="mt-3">
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>产品</TableHead>
                    <TableHead className="w-24">差评率</TableHead>
                    <TableHead>核心问题</TableHead>
                    <TableHead className="w-16">待复盘</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {summary.risk_products.map((item) => (
                    <TableRow key={`${item.product_id ?? item.product_name}-${item.top_issue}`}>
                      <TableCell className="text-sm font-semibold text-ink">{item.product_name}</TableCell>
                      <TableCell className="text-sm text-[#d94d72]">{item.negative_rate.toFixed(1)}%</TableCell>
                      <TableCell className="text-sm text-soft">{item.top_issue}</TableCell>
                      <TableCell className="text-sm text-soft">{item.pending_review_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="mt-3 rounded-card border border-dashed border-line bg-white px-5 py-5 text-sm text-soft">
                {t("riskProductsEmpty")}
              </div>
            )}
          </div>

          <div className="space-y-4">
            <div className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
              <h3 className="font-heading text-lg font-extrabold tracking-normal text-ink">{t("pendingTrackers")}</h3>
              {summary.pending_trackers.length > 0 ? (
                <div className="mt-3 space-y-2">
                  {summary.pending_trackers.map((item) => (
                    <div
                      key={`${item.title}-${item.tag_name}`}
                      className="flex items-center justify-between rounded-card border border-line bg-[#fbf9ff] px-4 py-3"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-ink">{item.title}</div>
                        <div className="text-xs text-soft">
                          {item.product_name} · {item.tag_name} · {item.status}
                        </div>
                      </div>
                      <div className="shrink-0 text-xs tabular-nums text-soft">
                        {item.baseline_pct === null ? "—" : `${item.baseline_pct.toFixed(1)}%`} → {item.current_pct === null ? "—" : `${item.current_pct.toFixed(1)}%`}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-3 rounded-card border border-dashed border-line bg-white px-5 py-5 text-sm text-soft">
                  {t("pendingTrackersEmpty")}
                </div>
              )}
            </div>

            <div className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
              <h3 className="font-heading text-lg font-extrabold tracking-normal text-ink">{t("roleActions")}</h3>
              {actionOwnershipSummary.length > 0 ? (
                <div className="mt-3 space-y-1.5">
                  {actionOwnershipSummary.map((item) => (
                    <div
                      key={item.responsibility}
                      className="flex items-center justify-between rounded-card border border-line bg-white px-4 py-2.5"
                    >
                      <span className="text-sm font-semibold text-ink">{item.responsibility}</span>
                      <span className="font-heading text-lg font-extrabold text-ink">{item.count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-3 rounded-card border border-dashed border-line bg-white px-5 py-5 text-sm text-soft">
                  {t("roleActionsEmpty")}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Recent Uploads */}
        <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
          <h3 className="font-heading text-lg font-extrabold tracking-normal text-ink">{t("recentUploads")}</h3>
          {summary.recent_sessions.length > 0 ? (
            <Table className="mt-3">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>批次名称</TableHead>
                  <TableHead className="w-28">产品</TableHead>
                  <TableHead className="w-24">目的</TableHead>
                  <TableHead className="w-20">评论数</TableHead>
                  <TableHead className="w-28">时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.recent_sessions.map((item) => (
                  <TableRow key={item.session_id}>
                    <TableCell className="text-sm font-semibold text-ink">{item.title}</TableCell>
                    <TableCell className="text-sm text-soft">{item.product_id}</TableCell>
                    <TableCell className="text-sm text-soft">{item.workflow_purpose}</TableCell>
                    <TableCell className="text-sm text-soft">{item.total_reviews}</TableCell>
                    <TableCell className="text-xs text-soft">{item.created_at}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="mt-3 rounded-card border border-dashed border-line bg-white px-5 py-5 text-sm text-soft">
              {t("recentUploadsEmpty")}
            </div>
          )}
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
