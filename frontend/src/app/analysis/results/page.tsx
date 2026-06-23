import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import {
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Target,
  Users,
  TrendingUp,
  TrendingDown,
  ShoppingCart,
  AlertCircle,
  Lightbulb,
  ChevronRight,
} from "lucide-react";

import { AppShell } from "@/components/app/app-shell";
import { AnalysisPollingPanel } from "@/components/analysis/analysis-polling-panel";
import { CreateActionPanel } from "@/components/analysis/create-action-panel";
import { InlineActionButton } from "@/components/analysis/inline-action-button";
import { ModuleCard } from "@/components/analysis/module-card";
import { getAnalysisSessionResults } from "@/lib/api/server";
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

function PctBadge({ pct, variant }: { pct: number; variant: "positive" | "negative" | "neutral" }) {
  const colors = {
    positive: "bg-[#ecfdf5] text-[#047857] border-[#a7f3d0]",
    negative: "bg-[#fef2f2] text-[#b91c1c] border-[#fecaca]",
    neutral: "bg-[#f5f3ff] text-[#6d28d9] border-[#ddd6fe]",
  };
  return (
    <span className={`inline-flex items-center rounded-pill border px-2.5 py-1 text-xs font-bold tabular-nums ${colors[variant]}`}>
      {pct.toFixed(1)}%
    </span>
  );
}

function TagRow({
  tag,
  pct,
  reason,
  variant,
  rank,
}: {
  tag: string;
  pct: number;
  reason: string;
  variant: "positive" | "negative" | "neutral";
  rank: number;
}) {
  const barColor = variant === "positive" ? "bg-[#10b981]" : variant === "negative" ? "bg-[#ef4444]" : "bg-[#8b5cf6]";
  return (
    <div className="group flex items-start gap-4 rounded-card border border-line bg-white px-4 py-3.5 transition hover:shadow-sm">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#f8f6fa] text-xs font-bold text-soft">
        {rank}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-ink">{tag}</span>
          <PctBadge pct={pct} variant={variant} />
        </div>
        <div className="mt-1.5 h-1.5 w-full max-w-[200px] overflow-hidden rounded-full bg-[#f3f0f5]">
          <div className={`h-full rounded-full ${barColor} transition-all`} style={{ width: `${Math.min(pct, 100)}%` }} />
        </div>
        {reason && reason !== "No representative comment found." && (
          <p className="mt-2 text-xs leading-5 text-soft italic">
            &ldquo;{reason.length > 140 ? reason.slice(0, 140) + "..." : reason}&rdquo;
          </p>
        )}
      </div>
    </div>
  );
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
      <div className="mt-1.5 text-sm font-bold text-ink">{value}</div>
      {detail && <p className="mt-1 text-xs leading-5 text-soft">{detail}</p>}
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

  if (!sessionId && jobId) {
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

  if (!sessionId) {
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

  let payload;
  try {
    payload = await getAnalysisSessionResults(sessionId);
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

  return (
    <AppShell
      currentPath="/analysis/results"
      title={t("title")}
      description={t("description")}
    >
      {/* Header */}
      <section className="rounded-shell border border-line bg-white p-6 shadow-card">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              {payload.session.custom_title || payload.session.auto_title || payload.session.product_id}
            </h2>
            <div className="mt-2 flex flex-wrap gap-2">
              <span className="rounded-pill border border-line bg-[#faf8fb] px-3 py-1.5 text-xs font-medium text-soft">
                {renderValue(context.time_label)}
              </span>
              <span className="rounded-pill border border-line bg-[#faf8fb] px-3 py-1.5 text-xs font-medium text-soft">
                {renderValue(context.workflow_purpose, t("purposeNotSetLabel"))}
              </span>
              <span className="rounded-pill border border-line bg-[#faf8fb] px-3 py-1.5 text-xs font-medium text-soft">
                {payload.comments.length} {t("reviews")}
              </span>
            </div>
          </div>
          <div className="flex gap-2">
            <Link
              href={`/analysis/compare?product_id=${encodeURIComponent(payload.session.product_id)}&session_id=${sessionId}`}
              className="inline-flex min-h-10 items-center justify-center rounded-pill bg-ink px-4 py-2.5 text-sm font-semibold text-white shadow-card"
            >
              {t("goCompare")}
            </Link>
            <Link
              href="/analysis/history"
              className="inline-flex min-h-10 items-center justify-center rounded-pill border border-line bg-white px-4 py-2.5 text-sm font-semibold text-ink"
            >
              {t("backHistory")}
            </Link>
          </div>
        </div>
      </section>

      {/* Metrics Row */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex items-center gap-3 rounded-card border border-line bg-white p-4 shadow-sm">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#f5f3ff]">
            <MessageSquare className="h-5 w-5 text-[#7c3aed]" />
          </div>
          <div>
            <div className="text-xs font-medium text-soft">{t("totalReviews")}</div>
            <div className="font-heading text-2xl font-bold text-ink">{payload.session.total_reviews}</div>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-card border border-line bg-white p-4 shadow-sm">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#ecfdf5]">
            <ThumbsUp className="h-5 w-5 text-[#059669]" />
          </div>
          <div>
            <div className="text-xs font-medium text-soft">{t("positive")}</div>
            <div className="font-heading text-2xl font-bold text-[#059669]">{payload.session.positive_count}</div>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-card border border-line bg-white p-4 shadow-sm">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#fef2f2]">
            <ThumbsDown className="h-5 w-5 text-[#dc2626]" />
          </div>
          <div>
            <div className="text-xs font-medium text-soft">{t("negative")}</div>
            <div className="font-heading text-2xl font-bold text-[#dc2626]">{payload.session.negative_count}</div>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-card border border-line bg-white p-4 shadow-sm">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#fff7ed]">
            <Target className="h-5 w-5 text-[#d97706]" />
          </div>
          <div>
            <div className="text-xs font-medium text-soft">{t("purpose")}</div>
            <div className="text-sm font-semibold text-ink">{payload.session.workflow_purpose || t("purposeNotSet")}</div>
          </div>
        </div>
      </section>

      {/* Warnings */}
      {payload.session.warnings_json && payload.session.warnings_json.length > 0 && (
        <section className="rounded-card border border-amber-200 bg-amber-50/80 p-4 shadow-sm">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
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

      {/* Module 1: Consumer Profile */}
      <ModuleCard sessionId={sessionId} moduleKey="consumer_profile" moduleData={payload.modules?.consumer_profile as Record<string, unknown> || {}}>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#eef6ff]">
            <Users className="h-5 w-5 text-[#2563eb]" />
          </div>
          <div>
            <h3 className="font-heading text-lg font-bold text-ink">{t("moduleConsumerProfile")}</h3>
            <p className="text-xs text-soft">{t("moduleConsumerProfileDesc")}</p>
          </div>
        </div>
        <p className="mt-4 text-sm leading-7 text-ink">{consumerProfile.summary}</p>
        <div className="mt-4 space-y-2">
          {consumerProfile.rows.map((row, index) => (
            <div key={`consumer-${index}`} className="flex gap-3 rounded-card border border-line bg-[#faf8fb] px-4 py-3">
              <span className="shrink-0 text-xs font-bold uppercase tracking-[0.08em] text-soft">{renderValue(row.label)}</span>
              <span className="text-sm text-ink">{renderValue(row.detail)}</span>
            </div>
          ))}
        </div>
        {consumerProfile.evidence.length > 0 && (
          <div className="mt-4 rounded-card border border-dashed border-line bg-[#fdfcfe] p-4">
            <div className="text-xs font-semibold uppercase tracking-[0.08em] text-soft">{t("evidence")}</div>
            <div className="mt-2 space-y-1.5">
              {consumerProfile.evidence.map((quote, index) => (
                <p key={`evidence-${index}`} className="text-xs italic leading-5 text-soft">
                  &ldquo;{quote}&rdquo;
                </p>
              ))}
            </div>
          </div>
        )}
      </ModuleCard>

      {/* Module 2: User Experience — positive & negative TOP 10 */}
      <ModuleCard sessionId={sessionId} moduleKey="user_experience" moduleData={payload.modules?.user_experience as Record<string, unknown> || {}}>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#f0fdf4]">
            <TrendingUp className="h-5 w-5 text-[#16a34a]" />
          </div>
          <div>
            <h3 className="font-heading text-lg font-bold text-ink">{t("moduleUserExperience")}</h3>
            <p className="text-xs text-soft">{t("moduleUserExperienceDesc")}</p>
          </div>
        </div>
        <p className="mt-4 text-sm leading-7 text-ink">{userExperience.summary}</p>

        <div className="mt-5 grid gap-5 xl:grid-cols-2">
          {/* Positive */}
          <div>
            <div className="mb-3 flex items-center gap-2">
              <ThumbsUp className="h-4 w-4 text-[#059669]" />
              <span className="text-sm font-semibold text-[#059669]">{t("positiveFeedback")}</span>
              <span className="text-xs text-soft">TOP {userExperience.positive.length}</span>
            </div>
            <div className="space-y-2">
              {userExperience.positive.map((row, index) => (
                <TagRow
                  key={`pos-${index}`}
                  tag={String(row.tag || row.label || `#${index + 1}`)}
                  pct={Number(row.pct || 0)}
                  reason={String(row.reason || row.detail || "")}
                  variant="positive"
                  rank={index + 1}
                />
              ))}
              {userExperience.positive.length === 0 && (
                <p className="text-sm text-soft">{t("noPositive")}</p>
              )}
            </div>
          </div>

          {/* Negative */}
          <div>
            <div className="mb-3 flex items-center gap-2">
              <ThumbsDown className="h-4 w-4 text-[#dc2626]" />
              <span className="text-sm font-semibold text-[#dc2626]">{t("negativeFeedback")}</span>
              <span className="text-xs text-soft">TOP {userExperience.negative.length}</span>
            </div>
            <div className="space-y-2">
              {userExperience.negative.map((row, index) => (
                <div key={`neg-wrapper-${index}`} className="group relative">
                  <TagRow
                    tag={String(row.tag || row.label || `#${index + 1}`)}
                    pct={Number(row.pct || 0)}
                    reason={String(row.reason || row.detail || "")}
                    variant="negative"
                    rank={index + 1}
                  />
                  <div className="absolute right-2 top-2">
                    <InlineActionButton
                      sessionId={sessionId}
                      productId={payload.session.product_ref_id}
                      sourceProductId={payload.session.product_id}
                      sourceVersion={payload.session.version}
                      tag={String(row.tag || row.label || "")}
                      pct={Number(row.pct || 0)}
                      reason={String(row.reason || row.detail || "")}
                    />
                  </div>
                </div>
              ))}
              {userExperience.negative.length === 0 && (
                <p className="text-sm text-soft">{t("noNegative")}</p>
              )}
            </div>
          </div>
        </div>
      </ModuleCard>

      {/* Module 3: Purchase Motives */}
      <ModuleCard sessionId={sessionId} moduleKey="purchase_motives" moduleData={payload.modules?.purchase_motives as Record<string, unknown> || {}}>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#fffbeb]">
            <ShoppingCart className="h-5 w-5 text-[#d97706]" />
          </div>
          <div>
            <h3 className="font-heading text-lg font-bold text-ink">{t("modulePurchaseMotives")}</h3>
            <p className="text-xs text-soft">{t("modulePurchaseMotivesDesc")}</p>
          </div>
        </div>
        <p className="mt-4 text-sm leading-7 text-ink">{purchaseMotives.summary}</p>
        <div className="mt-4 space-y-2">
          {purchaseMotives.rows.map((row, index) => (
            <TagRow
              key={`motive-${index}`}
              tag={String(row.tag || row.label || `#${index + 1}`)}
              pct={Number(row.pct || 0)}
              reason={String(row.reason || row.detail || "")}
              variant="positive"
              rank={index + 1}
            />
          ))}
        </div>
      </ModuleCard>

      {/* Module 4: Unmet Needs */}
      <ModuleCard sessionId={sessionId} moduleKey="unmet_needs" moduleData={payload.modules?.unmet_needs as Record<string, unknown> || {}}>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#fef2f2]">
            <TrendingDown className="h-5 w-5 text-[#dc2626]" />
          </div>
          <div>
            <h3 className="font-heading text-lg font-bold text-ink">{t("moduleUnmetNeeds")}</h3>
            <p className="text-xs text-soft">{t("moduleUnmetNeedsDesc")}</p>
          </div>
        </div>
        <p className="mt-4 text-sm leading-7 text-ink">{unmetNeeds.summary}</p>
        <div className="mt-4 space-y-2">
          {unmetNeeds.rows.map((row, index) => (
            <div key={`need-wrapper-${index}`} className="group relative">
              <TagRow
                tag={String(row.tag || row.label || `#${index + 1}`)}
                pct={Number(row.pct || 0)}
                reason={String(row.reason || row.detail || "")}
                variant="negative"
                rank={index + 1}
              />
              <div className="absolute right-2 top-2">
                <InlineActionButton
                  sessionId={sessionId}
                  productId={payload.session.product_ref_id}
                  sourceProductId={payload.session.product_id}
                  sourceVersion={payload.session.version}
                  tag={String(row.tag || row.label || "")}
                  pct={Number(row.pct || 0)}
                  reason={String(row.reason || row.detail || "")}
                />
              </div>
            </div>
          ))}
        </div>
      </ModuleCard>

      {/* Module 5: Recommendations */}
      <ModuleCard sessionId={sessionId} moduleKey="recommendations" moduleData={payload.modules?.recommendations as Record<string, unknown> || {}}>
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#faf5ff]">
            <Lightbulb className="h-5 w-5 text-[#7c3aed]" />
          </div>
          <div>
            <h3 className="font-heading text-lg font-bold text-ink">{t("moduleRecommendations")}</h3>
            <p className="text-xs text-soft">{t("moduleRecommendationsDesc")}</p>
          </div>
        </div>
        <p className="mt-4 text-sm leading-7 text-ink">{recommendations.summary}</p>
        <div className="mt-4 space-y-3">
          {recommendations.rows.map((row, index) => (
            <div key={`rec-${index}`} className="flex items-start gap-3 rounded-card border border-line bg-[#faf8fb] px-4 py-3.5">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#7c3aed] text-xs font-bold text-white">
                {index + 1}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold text-ink">
                  {renderValue(row.label || row.tag || row.title)}
                </div>
                <p className="mt-1 text-sm leading-6 text-soft">
                  {renderValue(row.detail || row.reason || row.summary || row.value)}
                </p>
              </div>
              <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-soft/50" />
            </div>
          ))}
        </div>
      </ModuleCard>

      {/* Create Action Panel */}
      <CreateActionPanel
        sessionId={sessionId}
        productId={payload.session.product_ref_id}
        sourceProductId={payload.session.product_id}
        sourceVersion={payload.session.version}
        sourceBatchLabel={payload.session.custom_title || payload.session.auto_title || payload.session.version}
        candidates={actionCandidates.filter(
          (item) => item.label || item.detail || item.suggestedAction,
        )}
      />

      {/* Module 6: Raw Reviews */}
      <section className="rounded-shell border border-line bg-white p-6 shadow-card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#f8f6fa]">
              <MessageSquare className="h-5 w-5 text-soft" />
            </div>
            <div>
              <h3 className="font-heading text-lg font-bold text-ink">{t("rawReviews")}</h3>
              <p className="text-xs text-soft">{t("rawReviewsDesc")}</p>
            </div>
          </div>
          <Link
            href={`/analysis/compare?product_id=${encodeURIComponent(payload.session.product_id)}`}
            className="inline-flex min-h-9 items-center justify-center rounded-pill bg-ink px-4 py-2 text-xs font-semibold text-white shadow-sm"
          >
            {t("goCompareDetail")}
          </Link>
        </div>

        <div className="mt-5 space-y-2">
          {payload.comments.length > 0 ? (
            payload.comments.slice(0, 20).map((comment, index) => {
              const sentiment = String(comment.sentiment || "");
              const sentimentColor = sentiment === "positive"
                ? "text-[#059669] bg-[#ecfdf5] border-[#a7f3d0]"
                : sentiment === "negative"
                  ? "text-[#dc2626] bg-[#fef2f2] border-[#fecaca]"
                  : "text-soft bg-[#f8f6fa] border-line";
              return (
                <div key={String(comment.id ?? index)} className="rounded-card border border-line bg-white px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-soft">{renderValue(comment.date, t("noDate"))}</span>
                    <span className={`rounded-pill border px-2 py-0.5 text-[10px] font-semibold ${sentimentColor}`}>
                      {sentiment || t("noSentiment")}
                    </span>
                    {comment.issue_tag ? (
                      <span className="rounded-pill border border-[#fecaca] bg-[#fef2f2] px-2 py-0.5 text-[10px] text-[#b91c1c]">
                        {String(comment.issue_tag)}
                      </span>
                    ) : null}
                    {comment.highlight_tag ? (
                      <span className="rounded-pill border border-[#a7f3d0] bg-[#ecfdf5] px-2 py-0.5 text-[10px] text-[#047857]">
                        {String(comment.highlight_tag)}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1.5 text-sm leading-6 text-ink">
                    {renderValue(comment.content, "")}
                  </p>
                </div>
              );
            })
          ) : (
            <div className="rounded-card border border-dashed border-line bg-[#fdfcfe] px-5 py-8 text-center text-sm text-soft">
              {t("noReviews")}
            </div>
          )}
        </div>
      </section>
    </AppShell>
  );
}
