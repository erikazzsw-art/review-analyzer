import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import {
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Target,
  AlertCircle,
} from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { AnalysisPollingPanel } from "@/components/analysis/analysis-polling-panel";
import { AnalysisResultsSections } from "@/components/analysis/analysis-results-sections";
import { ResultsFilterBar } from "@/components/analysis/results-filter-bar";
import {
  getAnalysisHistory,
  getAnalysisResults,
  getAnalysisSessionResults,
} from "@/lib/api/server";
import { isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Analysis Results | ClueAI",
  description: "Authenticated analysis results for a single review batch.",
});

type ResultsPageProps = {
  searchParams?: Promise<{
    session_id?: string;
    job_id?: string;
    product_id?: string;
    range?: string;
    start?: string;
    end?: string;
  }>;
};

function renderValue(value: unknown, fallback = "--"): string {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function normalizeModule(
  module: Partial<{
    summary: unknown;
    rows: unknown;
    evidence: unknown;
    positive: unknown;
    negative: unknown;
  }> | undefined,
): {
  summary: string;
  rows: Array<Record<string, unknown>>;
  evidence: string[];
  positive: Array<Record<string, unknown>>;
  negative: Array<Record<string, unknown>>;
} {
  return {
    summary: renderValue(module?.summary, ""),
    rows: Array.isArray(module?.rows) ? (module.rows as Array<Record<string, unknown>>) : [],
    evidence: Array.isArray(module?.evidence)
      ? (module.evidence as string[]).map((item) => renderValue(item, ""))
      : [],
    positive: Array.isArray(module?.positive)
      ? (module.positive as Array<Record<string, unknown>>)
      : [],
    negative: Array.isArray(module?.negative)
      ? (module.negative as Array<Record<string, unknown>>)
      : [],
  };
}

function CalloutCard({
  variant,
  label,
  value,
  detail,
}: {
  variant: "issue" | "highlight";
  label: string;
  value: string;
  detail?: string;
}) {
  const styles = {
    issue: "border-l-[#ef4444] bg-[#fef8f8]",
    highlight: "border-l-[#10b981] bg-[#f0fdf8]",
  };
  return (
    <div className={`rounded-card border border-line border-l-4 ${styles[variant]} p-4`}>
      <div className="text-xs font-semibold uppercase tracking-[0.08em] text-soft">{label}</div>
      <div className="mt-1 text-sm font-bold text-ink">{value}</div>
      {detail && <p className="mt-0.5 text-xs leading-5 text-soft">{detail}</p>}
    </div>
  );
}

export default async function AnalysisResultsPage({
  searchParams,
}: ResultsPageProps) {
  const t = await getTranslations("analysis");
  const params = searchParams ? await searchParams : undefined;
  const sessionId = Number(params?.session_id || 0);
  const jobId = Number(params?.job_id || 0);
  const productIdParam = (params?.product_id || "").trim();
  const rangeParam = (params?.range || "").trim() || "default";
  const startParam = (params?.start || "").trim() || null;
  const endParam = (params?.end || "").trim() || null;

  // job 状态轮询 — 上传完成跳到 polling
  if (!sessionId && !productIdParam && jobId) {
    return (
      <AppShell
        currentPath="/analysis/results"
        title={t("title")}
        description={t("description")}
      >
        <AnalysisPollingPanel jobId={jobId} />
      </AppShell>
    );
  }

  // 全空 → 找最新 session,redirect 到 product_id + session_id
  if (!sessionId && !productIdParam) {
    let latestId = 0;
    let latestProductId = "";
    try {
      const history = await getAnalysisHistory();
      let latestCreatedAt = "";
      for (const product of history.items) {
        for (const session of product.sessions) {
          if (!latestCreatedAt || session.created_at > latestCreatedAt) {
            latestCreatedAt = session.created_at;
            latestId = session.id;
            latestProductId = session.product_id;
          }
        }
      }
    } catch (error: unknown) {
      if (isApiError(error) && error.status === 401) {
        redirect("/login");
      }
    }
    if (latestId && latestProductId) {
      redirect(
        `/analysis/results?product_id=${encodeURIComponent(latestProductId)}&range=default&session_id=${latestId}`,
      );
    }

    return (
      <AppShell
        currentPath="/analysis/results"
        title={t("noSessionId")}
        description={t("noSessionIdDesc")}
      >
        <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <p className="text-sm leading-7 text-soft">
            {t("noSessionIdHint")}
          </p>
          <Link
            href="/analysis/history"
            className="mt-5 inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
          >
            {t("goHistory")}
          </Link>
        </section>
      </AppShell>
    );
  }

  // 老链接兼容：只有 session_id → 查 session 推断 product_id 后 redirect
  if (sessionId && !productIdParam) {
    try {
      const payload = await getAnalysisSessionResults(sessionId);
      redirect(
        `/analysis/results?product_id=${encodeURIComponent(payload.session.product_id)}&range=default&session_id=${sessionId}`,
      );
    } catch (error: unknown) {
      if (isApiError(error) && error.status === 401) {
        redirect("/login");
      }
      // 404 / 其他错误：走 fallthrough 显示错误
    }
  }

  // 主路径：按 product_id + range 拉聚合结果
  let payload;
  try {
    payload = await getAnalysisResults({
      productId: productIdParam,
      range: rangeParam,
      start: startParam,
      end: endParam,
      sessionId: sessionId || null,
    });
  } catch (error: unknown) {
    if (isApiError(error) && error.status === 401) {
      redirect("/login");
    }
    return (
      <AppShell
        currentPath="/analysis/results"
        title={t("loadError")}
        description=""
      >
        <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <p className="text-sm leading-7 text-soft">
            {isApiError(error) && error.status === 404
              ? t("notFound")
              : t("loadException")}
          </p>
          <Link
            href="/analysis/history"
            className="mt-5 inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
          >
            {t("backHistory")}
          </Link>
        </section>
      </AppShell>
    );
  }

  const context = payload.context as {
    product_id?: string;
    version?: string;
    time_label?: string;
    workflow_purpose?: string;
  };
  const consumerProfile = normalizeModule(payload.modules?.consumer_profile);
  const userExperience = normalizeModule(payload.modules?.user_experience);
  const purchaseMotives = normalizeModule(payload.modules?.purchase_motives);
  const unmetNeeds = normalizeModule(payload.modules?.unmet_needs);
  const recommendations = normalizeModule(payload.modules?.recommendations);

  const topIssue = userExperience.negative[0];
  const topHighlight = userExperience.positive[0];

  const actionCandidates = [
    ...(userExperience.negative || []).map((row) => ({
      label: String(row.tag || row.label || "问题"),
      detail: String(row.reason || row.detail || row.pct || ""),
      currentPct: typeof row.pct === "number" ? row.pct : Number(row.pct) || null,
      suggestedAction: String(row.reason || row.detail || ""),
    })),
    ...(unmetNeeds.rows || []).map((row) => ({
      label: String(row.tag || row.label || "需求"),
      detail: String(row.reason || row.detail || row.summary || row.value || ""),
      currentPct: typeof row.pct === "number" ? row.pct : Number(row.pct) || null,
      suggestedAction: String(row.reason || row.detail || ""),
    })),
  ].slice(0, 8);

  const tStrings: Record<string, string> = {
    tabOverview: "概览",
    tabProfile: "画像 & 动机",
    tabNeeds: "需求 & 建议",
    moduleConsumerProfile: t("moduleConsumerProfile"),
    moduleUserExperience: t("moduleUserExperience"),
    modulePurchaseMotives: t("modulePurchaseMotives"),
    moduleUnmetNeeds: t("moduleUnmetNeeds"),
    moduleRecommendations: t("moduleRecommendations"),
    moduleConsumerProfileDesc: t("moduleConsumerProfileDesc"),
    moduleUserExperienceDesc: t("moduleUserExperienceDesc"),
    modulePurchaseMotivesDesc: t("modulePurchaseMotivesDesc"),
    moduleUnmetNeedsDesc: t("moduleUnmetNeedsDesc"),
    moduleRecommendationsDesc: t("moduleRecommendationsDesc"),
    evidence: t("evidence"),
    positiveFeedback: t("positiveFeedback"),
    negativeFeedback: t("negativeFeedback"),
    noPositive: t("noPositive"),
    noNegative: t("noNegative"),
    rawReviews: t("rawReviews"),
    noDate: t("noDate"),
    noSentiment: t("noSentiment"),
    noReviews: t("noReviews"),
  };

  const isAggregated = Boolean(payload.is_aggregated);

  const filterBarSlot = (
    <ResultsFilterBar
      productId={payload.session.product_id}
      range={payload.range || rangeParam}
      start={payload.range_start || startParam}
      end={payload.range_end || endParam}
      timeLabel={context.time_label}
      isAggregated={isAggregated}
    />
  );

  const overviewSlot = (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <section className="rounded-shell border border-line bg-white p-5 shadow-card">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="font-heading text-xl font-extrabold tracking-[-0.04em] text-ink">
              {payload.session.custom_title || payload.session.auto_title || payload.session.product_id}
            </h2>
            <div className="mt-1.5 flex flex-wrap gap-2">
              <span className="rounded-pill border border-line bg-[#faf8fb] px-3 py-1 text-xs font-medium text-soft">
                {renderValue(context.time_label)}
              </span>
              <span className="rounded-pill border border-line bg-[#faf8fb] px-3 py-1 text-xs font-medium text-soft">
                {renderValue(context.workflow_purpose, t("purposeNotSetLabel"))}
              </span>
              <span className="rounded-pill border border-line bg-[#faf8fb] px-3 py-1 text-xs font-medium text-soft">
                {payload.comments.length} {t("reviews")}
              </span>
            </div>
          </div>
          <div className="flex gap-2">
            <Link
              href={`/analysis/compare?product_id=${encodeURIComponent(payload.session.product_id)}${sessionId ? `&session_id=${sessionId}` : ""}`}
              className="inline-flex min-h-9 items-center justify-center rounded-pill bg-ink px-4 py-2 text-sm font-semibold text-white shadow-card"
            >
              {t("goCompare")}
            </Link>
            <Link
              href="/analysis/history"
              className="inline-flex min-h-9 items-center justify-center rounded-pill border border-line bg-white px-4 py-2 text-sm font-semibold text-ink"
            >
              {t("backHistory")}
            </Link>
          </div>
        </div>
      </section>

      {/* Metrics Row */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex items-center gap-3 rounded-card border border-line bg-white p-3.5 shadow-sm">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#f5f3ff]">
            <MessageSquare className="h-4 w-4 text-[#7c3aed]" />
          </div>
          <div>
            <div className="text-xs font-medium text-soft">{t("totalReviews")}</div>
            <div className="font-heading text-xl font-bold text-ink">{payload.session.total_reviews}</div>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-card border border-line bg-white p-3.5 shadow-sm">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#ecfdf5]">
            <ThumbsUp className="h-4 w-4 text-[#059669]" />
          </div>
          <div>
            <div className="text-xs font-medium text-soft">{t("positive")}</div>
            <div className="font-heading text-xl font-bold text-[#059669]">{payload.session.positive_count}</div>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-card border border-line bg-white p-3.5 shadow-sm">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#fef2f2]">
            <ThumbsDown className="h-4 w-4 text-[#dc2626]" />
          </div>
          <div>
            <div className="text-xs font-medium text-soft">{t("negative")}</div>
            <div className="font-heading text-xl font-bold text-[#dc2626]">{payload.session.negative_count}</div>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-card border border-line bg-white p-3.5 shadow-sm">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#fff7ed]">
            <Target className="h-4 w-4 text-[#d97706]" />
          </div>
          <div>
            <div className="text-xs font-medium text-soft">{t("purpose")}</div>
            <div className="text-sm font-semibold text-ink">{payload.session.workflow_purpose || t("purposeNotSet")}</div>
          </div>
        </div>
      </section>

      {/* Warnings */}
      {payload.session.warnings_json && payload.session.warnings_json.length > 0 && (
        <section className="rounded-card border border-amber-200 bg-amber-50/80 p-3.5 shadow-sm">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            <div className="space-y-1">
              {payload.session.warnings_json.map((w: { message?: string; type?: string }, i: number) => (
                <p key={i} className="text-sm leading-6 text-amber-900">
                  {w.message || t("warningFallback")}
                </p>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Key Findings Callout */}
      {(topIssue || topHighlight) && (
        <section className="grid gap-3 md:grid-cols-2">
          {topHighlight && (
            <CalloutCard
              variant="highlight"
              label="TOP 亮点"
              value={String(topHighlight.tag || topHighlight.label || "")}
              detail={`${Number(topHighlight.pct || 0).toFixed(1)}% 的好评提及此项`}
            />
          )}
          {topIssue && (
            <CalloutCard
              variant="issue"
              label="TOP 问题"
              value={String(topIssue.tag || topIssue.label || "")}
              detail={`${Number(topIssue.pct || 0).toFixed(1)}% 的差评提及此项`}
            />
          )}
        </section>
      )}
    </div>
  );

  return (
    <AppShell
      currentPath="/analysis/results"
      title={t("title")}
      description={t("description")}
    >
      <AnalysisResultsSections
        sessionId={sessionId || 0}
        session={payload.session}
        consumerProfile={consumerProfile}
        userExperience={userExperience}
        purchaseMotives={purchaseMotives}
        unmetNeeds={unmetNeeds}
        recommendations={recommendations}
        modules={payload.modules || {}}
        comments={payload.comments}
        actionCandidates={actionCandidates}
        overviewSlot={overviewSlot}
        filterBarSlot={filterBarSlot}
        t={tStrings}
      />
    </AppShell>
  );
}
