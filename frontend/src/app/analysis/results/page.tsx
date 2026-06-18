import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app/app-shell";
import { CreateActionPanel } from "@/components/analysis/create-action-panel";
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
  }>;
};

const moduleLabelKeys: Record<string, string> = {
  consumer_profile: "moduleConsumerProfile",
  user_experience: "moduleUserExperience",
  purchase_motives: "modulePurchaseMotives",
  unmet_needs: "moduleUnmetNeeds",
  recommendations: "moduleRecommendations",
};

const moduleDescKeys: Record<string, string> = {
  consumer_profile: "moduleConsumerProfileDesc",
  user_experience: "moduleUserExperienceDesc",
  purchase_motives: "modulePurchaseMotivesDesc",
  unmet_needs: "moduleUnmetNeedsDesc",
  recommendations: "moduleRecommendationsDesc",
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

export default async function AnalysisResultsPage({
  searchParams,
}: ResultsPageProps) {
  const t = await getTranslations("analysis");
  const params = searchParams ? await searchParams : undefined;
  const sessionId = Number(params?.session_id || 0);

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
  ].slice(0, 5);

  return (
    <AppShell
      currentPath="/analysis/results"
      title={t("title")}
      description={t("description")}
    >
      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
          {t("badge")}
        </div>
        <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          {payload.session.custom_title || payload.session.auto_title || payload.session.product_id}
        </h2>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-soft">
            {renderValue(context.time_label)}
          </span>
          <span className="rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-soft">
            {renderValue(context.workflow_purpose, t("purposeNotSetLabel"))}
          </span>
          <span className="rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-soft">
            {payload.comments.length} {t("reviews")}
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href={`/analysis/compare?product_id=${encodeURIComponent(payload.session.product_id)}&session_id=${sessionId}`}
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
          >
            {t("goCompare")}
          </Link>
          <Link
            href="/analysis/history"
            className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-ink"
          >
            {t("backHistory")}
          </Link>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <div className="rounded-card border border-line bg-white/84 p-5 shadow-card backdrop-blur">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("totalReviews")}</div>
          <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
            {payload.session.total_reviews}
          </div>
        </div>
        <div className="rounded-card border border-line bg-white/84 p-5 shadow-card backdrop-blur">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("positive")}</div>
          <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-[#4b8f82]">
            {payload.session.positive_count}
          </div>
        </div>
        <div className="rounded-card border border-line bg-white/84 p-5 shadow-card backdrop-blur">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("negative")}</div>
          <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-[#d94d72]">
            {payload.session.negative_count}
          </div>
        </div>
        <div className="rounded-card border border-line bg-white/84 p-5 shadow-card backdrop-blur">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("purpose")}</div>
          <div className="mt-3 text-sm leading-7 text-ink">
            {payload.session.workflow_purpose || t("purposeNotSet")}
          </div>
        </div>
      </section>

      {payload.session.warnings_json && payload.session.warnings_json.length > 0 && (
        <section className="rounded-card border border-amber-200 bg-amber-50/80 p-4 shadow-card backdrop-blur">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 text-lg">⚠️</span>
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

      <section className="space-y-5">
        <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
            1 · {t(moduleLabelKeys["consumer_profile"])}
          </div>
          <p className="mt-4 text-sm leading-7 text-soft">{consumerProfile.summary}</p>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {consumerProfile.rows.map((row, index) => (
              <div key={`consumer-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                  {renderValue(row.label || row.tag || `#${index + 1}`)}
                </div>
                <div className="mt-2 text-sm leading-7 text-ink">
                  {renderValue(row.detail || row.reason || row.summary || row.value)}
                </div>
              </div>
            ))}
          </div>
          {consumerProfile.evidence.length > 0 ? (
            <div className="mt-5 rounded-card border border-line bg-[#fffafc] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                {t("evidence")}
              </div>
              <div className="mt-3 space-y-2 text-sm leading-7 text-ink">
                {consumerProfile.evidence.map((quote, index) => (
                  <p key={`consumer-evidence-${index}`}>- {quote}</p>
                ))}
              </div>
            </div>
          ) : null}
        </article>

        <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
            2 · {t(moduleLabelKeys["user_experience"])}
          </div>
          <p className="mt-4 text-sm leading-7 text-soft">{userExperience.summary}</p>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <div className="rounded-card border border-line bg-[#f8fffc] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("positiveFeedback")}</div>
              <div className="mt-3 space-y-3">
                {userExperience.positive.map((row, index) => (
                  <div key={`positive-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                    <div className="text-sm font-semibold text-ink">
                      {renderValue(row.tag || row.label || `#${index + 1}`)}
                    </div>
                    <div className="mt-2 text-sm leading-7 text-soft">
                      {renderValue(row.reason || row.detail || row.pct)}
                    </div>
                  </div>
                ))}
                {userExperience.positive.length === 0 ? (
                  <div className="text-sm leading-7 text-soft">{t("noPositive")}</div>
                ) : null}
              </div>
            </div>
            <div className="rounded-card border border-line bg-[#fff8f9] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">{t("negativeFeedback")}</div>
              <div className="mt-3 space-y-3">
                {userExperience.negative.map((row, index) => (
                  <div key={`negative-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                    <div className="text-sm font-semibold text-ink">
                      {renderValue(row.tag || row.label || `#${index + 1}`)}
                    </div>
                    <div className="mt-2 text-sm leading-7 text-soft">
                      {renderValue(row.reason || row.detail || row.pct)}
                    </div>
                  </div>
                ))}
                {userExperience.negative.length === 0 ? (
                  <div className="text-sm leading-7 text-soft">{t("noNegative")}</div>
                ) : null}
              </div>
            </div>
          </div>
        </article>

        <div className="grid gap-5 xl:grid-cols-2">
          <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
            <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
              3 · {t(moduleLabelKeys["purchase_motives"])}
            </div>
            <p className="mt-4 text-sm leading-7 text-soft">{purchaseMotives.summary}</p>
            <div className="mt-5 space-y-3">
              {purchaseMotives.rows.map((row, index) => (
                <div key={`motive-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                  <div className="text-sm font-semibold text-ink">
                    {renderValue(row.label || row.tag || `#${index + 1}`)}
                  </div>
                  <div className="mt-2 text-sm leading-7 text-soft">
                    {renderValue(row.detail || row.reason || row.summary || row.value)}
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
            <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
              4 · {t(moduleLabelKeys["unmet_needs"])}
            </div>
            <p className="mt-4 text-sm leading-7 text-soft">{unmetNeeds.summary}</p>
            <div className="mt-5 space-y-3">
              {unmetNeeds.rows.map((row, index) => (
                <div key={`need-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                  <div className="text-sm font-semibold text-ink">
                    {renderValue(row.label || row.tag || `#${index + 1}`)}
                  </div>
                  <div className="mt-2 text-sm leading-7 text-soft">
                    {renderValue(row.detail || row.reason || row.summary || row.value)}
                  </div>
                </div>
              ))}
            </div>
          </article>
        </div>

        <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
            5 · {t(moduleLabelKeys["recommendations"])}
          </div>
          <p className="mt-4 text-sm leading-7 text-soft">{recommendations.summary}</p>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {recommendations.rows.map((row, index) => (
              <div key={`recommend-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                <div className="text-sm font-semibold text-ink">
                  {renderValue(row.label || row.tag || row.title || `#${index + 1}`)}
                </div>
                <div className="mt-2 text-sm leading-7 text-soft">
                  {renderValue(row.detail || row.reason || row.summary || row.value)}
                </div>
              </div>
            ))}
          </div>
          {recommendations.evidence.length > 0 ? (
            <div className="mt-5 rounded-card border border-line bg-[#fffafc] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                {t("recommendBasis")}
              </div>
              <div className="mt-3 space-y-2 text-sm leading-7 text-ink">
                {recommendations.evidence.map((quote, index) => (
                  <p key={`recommend-evidence-${index}`}>- {quote}</p>
                ))}
              </div>
            </div>
          ) : null}
        </article>
      </section>

      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
          6 · {t("rawReviews")}
        </div>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              {t("rawReviews")}
            </h3>
            <p className="mt-2 text-sm leading-7 text-soft">
              {t("rawReviewsDesc")}
            </p>
          </div>
          <Link
            href={`/analysis/compare?product_id=${encodeURIComponent(payload.session.product_id)}`}
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
          >
            {t("goCompareDetail")}
          </Link>
        </div>

        <div className="mt-5 space-y-3">
          {payload.comments.length > 0 ? (
            payload.comments.slice(0, 24).map((comment, index) => (
              <div key={String(comment.id ?? index)} className="rounded-card border border-line bg-white px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                  {renderValue(comment.date, t("noDate"))} · {renderValue(comment.sentiment, t("noSentiment"))}
                </div>
                <div className="mt-2 text-sm leading-7 text-ink">
                  {renderValue(comment.content, "")}
                </div>
              </div>
            ))
          ) : (
            <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-5 py-6 text-sm leading-7 text-soft">
              {t("noReviews")}
            </div>
          )}
        </div>
      </section>
    </AppShell>
  );
}
