import Link from "next/link";
import { redirect } from "next/navigation";
import { isRedirectError } from "next/dist/client/components/redirect-error";
import { getLocale, getTranslations } from "next-intl/server";
import {
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Target,
  AlertCircle,
  Star,
} from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { AnalysisPollingPanel } from "@/components/analysis/analysis-polling-panel";
import { AnalysisResultsSections } from "@/components/analysis/analysis-results-sections";
import { AnalysisTabSwitcher } from "@/components/analysis/analysis-tab-switcher";
import { ResultsFilterBar } from "@/components/analysis/results-filter-bar";
import {
  getAnalysisHistory,
  getAnalysisResults,
  getAnalysisSessionResults,
} from "@/lib/api/server";
import { isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Analysis Results",
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
    version?: string;
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

function hasAspectEvidence(
  comment: Record<string, unknown>,
  tagKey: string,
): boolean {
  const aj = comment.aspects_json as
    | { aspects?: Array<{ key?: string; evidence_span?: string }>; cluster_propagated?: boolean }
    | null
    | undefined;
  if (!aj) return false;
  if (aj.cluster_propagated) return false;
  const aspects = aj.aspects;
  if (!Array.isArray(aspects)) return false;
  const content = String((comment as Record<string, unknown>).content || "");
  const norm = tagKey.toLowerCase().replace(/[\s_]+/g, "_");
  return aspects.some(
    (a) =>
      a.key?.toLowerCase().replace(/[\s_]+/g, "_") === norm &&
      !!a.evidence_span &&
      content.includes(a.evidence_span),
  );
}

function enrichRowsWithQuotes(
  rows: Array<Record<string, unknown>>,
  comments: Array<Record<string, unknown>>,
  source: "highlight_tag" | "issue_tag",
  perRow = 5,
): Array<Record<string, unknown>> {
  if (rows.length === 0 || comments.length === 0) return rows;
  return rows.map((row) => {
    const tag = String(row.tag || row.label || "").trim();
    if (!tag) return row;
    const quotes: string[] = [];
    const seen = new Set<string>();

    // Pass 1: comments with direct LLM evidence for this aspect
    for (const c of comments) {
      if (quotes.length >= perRow) break;
      if (!hasAspectEvidence(c, tag)) continue;
      const content = String((c as Record<string, unknown>).content || "").trim();
      if (!content || seen.has(content)) continue;
      seen.add(content);
      quotes.push(content);
    }

    // Pass 2: fall back to tag-field match if not enough verified quotes
    if (quotes.length < perRow) {
      for (const c of comments) {
        if (quotes.length >= perRow) break;
        const raw = String((c as Record<string, unknown>)[source] || "");
        const tags = raw.split(",").map((s) => s.trim());
        if (!tags.includes(tag)) continue;
        const content = String((c as Record<string, unknown>).content || "").trim();
        if (!content || seen.has(content)) continue;
        seen.add(content);
        quotes.push(content);
      }
    }

    if (quotes.length === 0) return row;
    return { ...row, representative_comments: quotes };
  });
}

export default async function AnalysisResultsPage({
  searchParams,
}: ResultsPageProps) {
  const t = await getTranslations("analysis");
  const locale = await getLocale();
  const params = searchParams ? await searchParams : undefined;
  const sessionId = Number(params?.session_id || 0);
  const jobId = Number(params?.job_id || 0);
  const productIdParam = (params?.product_id || "").trim();
  const rangeParam = (params?.range || "").trim() || "default";
  const startParam = (params?.start || "").trim() || null;
  const endParam = (params?.end || "").trim() || null;
  const versionParam = (params?.version || "").trim() || null;

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
      if (isRedirectError(error)) throw error;
      if (isApiError(error) && error.status === 401) {
        redirect("/login");
      }
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
      version: versionParam,
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
  const userExperienceRaw = normalizeModule(payload.modules?.user_experience);
  const userExperience = {
    ...userExperienceRaw,
    positive: enrichRowsWithQuotes(userExperienceRaw.positive, payload.comments, "highlight_tag", 5),
    negative: enrichRowsWithQuotes(userExperienceRaw.negative, payload.comments, "issue_tag", 5),
  };
  const purchaseMotives = normalizeModule(payload.modules?.purchase_motives);
  const unmetNeeds = normalizeModule(payload.modules?.unmet_needs);
  const recommendations = normalizeModule(payload.modules?.recommendations);

  const total = payload.session.total_reviews;
  const positivePct = total > 0 ? (payload.session.positive_count / total) * 100 : 0;
  const negativePct = total > 0 ? (payload.session.negative_count / total) * 100 : 0;

  const ratings = (payload.comments || [])
    .map((c) => Number((c as { rating?: number | null }).rating))
    .filter((r) => Number.isFinite(r) && r > 0);
  const avgRating = ratings.length > 0
    ? ratings.reduce((a, b) => a + b, 0) / ratings.length
    : null;

  const actionCandidates = [
    ...(userExperience.negative || []).map((row) => ({
      label: String(row.tag || row.label || t("negative")),
      detail: String(row.reason || row.detail || row.pct || ""),
      currentPct: typeof row.pct === "number" ? row.pct : Number(row.pct) || null,
      suggestedAction: String(row.reason || row.detail || ""),
    })),
    ...(unmetNeeds.rows || []).map((row) => ({
      label: String(row.tag || row.label || t("moduleUnmetNeeds")),
      detail: String(row.reason || row.detail || row.summary || row.value || ""),
      currentPct: typeof row.pct === "number" ? row.pct : Number(row.pct) || null,
      suggestedAction: String(row.reason || row.detail || ""),
    })),
  ].slice(0, 8);

  const isAggregated = Boolean(payload.is_aggregated);

  const filterBarSlot = (
    <ResultsFilterBar
      productId={payload.session.product_id}
      range={payload.range || rangeParam}
      start={payload.range_start || startParam}
      end={payload.range_end || endParam}
      timeLabel={context.time_label}
      isAggregated={isAggregated}
      version={versionParam}
    />
  );

  const showRating = avgRating !== null;
  const metricsGrid = showRating
    ? "grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
    : "grid gap-3 sm:grid-cols-2 lg:grid-cols-4";

  const overviewSlot = (
    <div className="flex flex-col gap-4">
      {/* Metrics Row */}
      <section className={metricsGrid}>
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
            <div className="text-xs font-medium text-soft">
              {t("positiveRate")}
              <span className="ml-0.5 text-[10px] text-soft/70">{t("sentimentSourceNote")}</span>
            </div>
            <div className="font-heading text-xl font-bold text-[#059669]">{positivePct.toFixed(1)}%</div>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-card border border-line bg-white p-3.5 shadow-sm">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#fef2f2]">
            <ThumbsDown className="h-4 w-4 text-[#dc2626]" />
          </div>
          <div>
            <div className="text-xs font-medium text-soft">
              {t("negativeRate")}
              <span className="ml-0.5 text-[10px] text-soft/70">{t("sentimentSourceNote")}</span>
            </div>
            <div className="font-heading text-xl font-bold text-[#dc2626]">{negativePct.toFixed(1)}%</div>
          </div>
        </div>
        {showRating && (
          <div className="flex items-center gap-3 rounded-card border border-line bg-white p-3.5 shadow-sm">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#fffbeb]">
              <Star className="h-4 w-4 text-[#d97706]" />
            </div>
            <div>
              <div className="text-xs font-medium text-soft">
                {t("rating")}
                <span className="ml-0.5 text-[10px] text-soft/70">（{t("ratingSource")}）</span>
              </div>
              <div className="font-heading text-xl font-bold text-ink">
                {avgRating!.toFixed(1)}
                <span className="ml-1 text-xs font-medium text-soft">/ 5</span>
              </div>
            </div>
          </div>
        )}
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
    </div>
  );

  const productRefId = (payload.session as { product_ref_id?: number | null }).product_ref_id;

  const resultsContent = (
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
      locale={locale}
    />
  );

  return (
    <AppShell
      currentPath="/analysis/results"
      title={t("title")}
      description={t("description")}
    >
      {productRefId != null && productRefId > 0 ? (
        <AnalysisTabSwitcher productId={productRefId}>
          {resultsContent}
        </AnalysisTabSwitcher>
      ) : (
        resultsContent
      )}
    </AppShell>
  );
}
