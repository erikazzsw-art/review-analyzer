"use client";

import type { ReactNode } from "react";
import {
  ThumbsUp,
  ThumbsDown,
  ChevronRight,
} from "lucide-react";

import {
  PageTabs,
  PageTabsList,
  PageTabsTrigger,
  PageTabsContent,
} from "@/components/ui/page-tabs";
import { ModuleCard } from "@/components/analysis/module-card";
import { InlineActionButton } from "@/components/analysis/inline-action-button";
import { CreateActionPanel } from "@/components/analysis/create-action-panel";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type TagItem = {
  tag: string;
  pct: number;
  reason: string;
};

type RowItem = Record<string, unknown>;

type NormalizedModule = {
  summary: string;
  rows: RowItem[];
  evidence: string[];
  positive: RowItem[];
  negative: RowItem[];
};

type SessionInfo = {
  product_ref_id?: number | null;
  product_id: string;
  version: string;
  custom_title?: string | null;
  auto_title?: string | null;
};

type ActionCandidate = {
  label: string;
  detail: string;
  currentPct: number | null;
  suggestedAction: string;
};

type Props = {
  sessionId: number;
  session: SessionInfo;
  consumerProfile: NormalizedModule;
  userExperience: NormalizedModule;
  purchaseMotives: NormalizedModule;
  unmetNeeds: NormalizedModule;
  recommendations: NormalizedModule;
  modules: Record<string, unknown>;
  comments: Array<Record<string, unknown>>;
  actionCandidates: ActionCandidate[];
  overviewSlot: ReactNode;
  t: Record<string, string>;
};

function rv(value: unknown, fallback = "--"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function PctBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-[#f3f0f5]">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-soft">
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

function TagTable({
  items,
  variant,
  sessionId,
  session,
  showAction,
}: {
  items: RowItem[];
  variant: "positive" | "negative" | "neutral";
  sessionId: number;
  session: SessionInfo;
  showAction?: boolean;
}) {
  const barColor =
    variant === "positive"
      ? "bg-[#10b981]"
      : variant === "negative"
        ? "bg-[#ef4444]"
        : "bg-[#8b5cf6]";

  if (items.length === 0) return null;

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead className="w-10 text-center">#</TableHead>
          <TableHead className="min-w-[120px]">标签</TableHead>
          <TableHead className="w-36">提及占比</TableHead>
          <TableHead>代表评论</TableHead>
          {showAction && <TableHead className="w-16" />}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((row, i) => {
          const tag = String(row.tag || row.label || `#${i + 1}`);
          const pct = Number(row.pct || 0);
          const reason = String(row.reason || row.detail || "");
          return (
            <TableRow key={`${variant}-${i}`} className="group">
              <TableCell className="text-center text-xs font-bold text-soft">
                {i + 1}
              </TableCell>
              <TableCell className="text-sm font-semibold text-ink">
                {tag}
              </TableCell>
              <TableCell>
                <PctBar pct={pct} color={barColor} />
              </TableCell>
              <TableCell className="max-w-xs text-xs leading-5 text-soft">
                {reason && reason !== "No representative comment found."
                  ? reason.length > 100
                    ? reason.slice(0, 100) + "..."
                    : reason
                  : "—"}
              </TableCell>
              {showAction && (
                <TableCell>
                  <InlineActionButton
                    sessionId={sessionId}
                    productId={session.product_ref_id}
                    sourceProductId={session.product_id}
                    sourceVersion={session.version}
                    tag={tag}
                    pct={pct}
                    reason={reason}
                  />
                </TableCell>
              )}
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

export function AnalysisResultsTabs({
  sessionId,
  session,
  consumerProfile,
  userExperience,
  purchaseMotives,
  unmetNeeds,
  recommendations,
  modules,
  comments,
  actionCandidates,
  overviewSlot,
  t,
}: Props) {
  return (
    <PageTabs defaultValue="overview">
      <div className="rounded-shell border border-line bg-white shadow-card">
        <PageTabsList>
          <PageTabsTrigger value="overview">{t.tabOverview || "概览"}</PageTabsTrigger>
          <PageTabsTrigger value="experience">{t.moduleUserExperience || "用户体验"}</PageTabsTrigger>
          <PageTabsTrigger value="profile">{t.tabProfile || "画像 & 动机"}</PageTabsTrigger>
          <PageTabsTrigger value="needs">{t.tabNeeds || "需求 & 建议"}</PageTabsTrigger>
          <PageTabsTrigger value="reviews">{t.rawReviews || "原始评论"}</PageTabsTrigger>
        </PageTabsList>
      </div>

      {/* Tab: 概览 */}
      <PageTabsContent value="overview">
        <div className="flex flex-col gap-4">
          {overviewSlot}

          {/* Module summaries */}
          <section className="rounded-shell border border-line bg-white p-5 shadow-card">
            <h3 className="text-sm font-semibold text-ink">{t.moduleConsumerProfile}</h3>
            <p className="mt-1.5 text-sm leading-6 text-soft">{consumerProfile.summary}</p>
          </section>
          <section className="rounded-shell border border-line bg-white p-5 shadow-card">
            <h3 className="text-sm font-semibold text-ink">{t.moduleUserExperience}</h3>
            <p className="mt-1.5 text-sm leading-6 text-soft">{userExperience.summary}</p>
          </section>
          <section className="rounded-shell border border-line bg-white p-5 shadow-card">
            <h3 className="text-sm font-semibold text-ink">{t.modulePurchaseMotives}</h3>
            <p className="mt-1.5 text-sm leading-6 text-soft">{purchaseMotives.summary}</p>
          </section>
          <section className="rounded-shell border border-line bg-white p-5 shadow-card">
            <h3 className="text-sm font-semibold text-ink">{t.moduleUnmetNeeds}</h3>
            <p className="mt-1.5 text-sm leading-6 text-soft">{unmetNeeds.summary}</p>
          </section>
        </div>
      </PageTabsContent>

      {/* Tab: 用户体验 */}
      <PageTabsContent value="experience">
        <ModuleCard
          sessionId={sessionId}
          moduleKey="user_experience"
          moduleData={(modules.user_experience as Record<string, unknown>) || {}}
        >
          <div className="grid gap-5 xl:grid-cols-2">
            <div>
              <div className="mb-3 flex items-center gap-2">
                <ThumbsUp className="h-4 w-4 text-[#059669]" />
                <span className="text-sm font-semibold text-[#059669]">
                  {t.positiveFeedback} TOP {userExperience.positive.length}
                </span>
              </div>
              <TagTable
                items={userExperience.positive}
                variant="positive"
                sessionId={sessionId}
                session={session}
              />
              {userExperience.positive.length === 0 && (
                <p className="text-sm text-soft">{t.noPositive}</p>
              )}
            </div>
            <div>
              <div className="mb-3 flex items-center gap-2">
                <ThumbsDown className="h-4 w-4 text-[#dc2626]" />
                <span className="text-sm font-semibold text-[#dc2626]">
                  {t.negativeFeedback} TOP {userExperience.negative.length}
                </span>
              </div>
              <TagTable
                items={userExperience.negative}
                variant="negative"
                sessionId={sessionId}
                session={session}
                showAction
              />
              {userExperience.negative.length === 0 && (
                <p className="text-sm text-soft">{t.noNegative}</p>
              )}
            </div>
          </div>
        </ModuleCard>
      </PageTabsContent>

      {/* Tab: 画像 & 动机 */}
      <PageTabsContent value="profile">
        <div className="flex flex-col gap-4">
          <ModuleCard
            sessionId={sessionId}
            moduleKey="consumer_profile"
            moduleData={(modules.consumer_profile as Record<string, unknown>) || {}}
          >
            <h3 className="text-base font-bold text-ink">{t.moduleConsumerProfile}</h3>
            <p className="mt-2 text-sm leading-6 text-soft">{t.moduleConsumerProfileDesc}</p>
            <p className="mt-3 text-sm leading-7 text-ink">{consumerProfile.summary}</p>
            {consumerProfile.rows.length > 0 && (
              <Table className="mt-4">
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="w-32">维度</TableHead>
                    <TableHead>详情</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {consumerProfile.rows.map((row, i) => (
                    <TableRow key={`cp-${i}`}>
                      <TableCell className="text-xs font-bold uppercase tracking-wide text-soft">
                        {rv(row.label)}
                      </TableCell>
                      <TableCell className="text-sm text-ink">{rv(row.detail)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            {consumerProfile.evidence.length > 0 && (
              <div className="mt-4 rounded-card border border-dashed border-line bg-[#fdfcfe] p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-soft">{t.evidence}</div>
                <div className="mt-2 space-y-1">
                  {consumerProfile.evidence.map((quote, i) => (
                    <p key={`ev-${i}`} className="text-xs italic leading-5 text-soft">
                      &ldquo;{quote}&rdquo;
                    </p>
                  ))}
                </div>
              </div>
            )}
          </ModuleCard>

          <ModuleCard
            sessionId={sessionId}
            moduleKey="purchase_motives"
            moduleData={(modules.purchase_motives as Record<string, unknown>) || {}}
          >
            <h3 className="text-base font-bold text-ink">{t.modulePurchaseMotives}</h3>
            <p className="mt-2 text-sm leading-6 text-soft">{t.modulePurchaseMotivesDesc}</p>
            <p className="mt-3 text-sm leading-7 text-ink">{purchaseMotives.summary}</p>
            <div className="mt-4">
              <TagTable
                items={purchaseMotives.rows}
                variant="positive"
                sessionId={sessionId}
                session={session}
              />
            </div>
          </ModuleCard>
        </div>
      </PageTabsContent>

      {/* Tab: 需求 & 建议 */}
      <PageTabsContent value="needs">
        <div className="flex flex-col gap-4">
          <ModuleCard
            sessionId={sessionId}
            moduleKey="unmet_needs"
            moduleData={(modules.unmet_needs as Record<string, unknown>) || {}}
          >
            <h3 className="text-base font-bold text-ink">{t.moduleUnmetNeeds}</h3>
            <p className="mt-2 text-sm leading-6 text-soft">{t.moduleUnmetNeedsDesc}</p>
            <p className="mt-3 text-sm leading-7 text-ink">{unmetNeeds.summary}</p>
            <div className="mt-4">
              <TagTable
                items={unmetNeeds.rows}
                variant="negative"
                sessionId={sessionId}
                session={session}
                showAction
              />
            </div>
          </ModuleCard>

          <ModuleCard
            sessionId={sessionId}
            moduleKey="recommendations"
            moduleData={(modules.recommendations as Record<string, unknown>) || {}}
          >
            <h3 className="text-base font-bold text-ink">{t.moduleRecommendations}</h3>
            <p className="mt-2 text-sm leading-6 text-soft">{t.moduleRecommendationsDesc}</p>
            <p className="mt-3 text-sm leading-7 text-ink">{recommendations.summary}</p>
            <div className="mt-4 space-y-2">
              {recommendations.rows.map((row, i) => (
                <div key={`rec-${i}`} className="flex items-start gap-3 rounded-card border border-line bg-[#faf8fb] px-4 py-3">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#7c3aed] text-xs font-bold text-white">
                    {i + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-ink">
                      {rv(row.label || row.tag || row.title)}
                    </div>
                    <p className="mt-0.5 text-sm leading-6 text-soft">
                      {rv(row.detail || row.reason || row.summary || row.value)}
                    </p>
                  </div>
                  <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-soft/50" />
                </div>
              ))}
            </div>
          </ModuleCard>

          <CreateActionPanel
            sessionId={sessionId}
            productId={session.product_ref_id}
            sourceProductId={session.product_id}
            sourceVersion={session.version}
            sourceBatchLabel={session.custom_title || session.auto_title || session.version}
            candidates={actionCandidates.filter(
              (item) => item.label || item.detail || item.suggestedAction,
            )}
          />
        </div>
      </PageTabsContent>

      {/* Tab: 原始评论 */}
      <PageTabsContent value="reviews">
        <section className="rounded-shell border border-line bg-white p-5 shadow-card">
          <div className="space-y-2">
            {comments.length > 0 ? (
              comments.slice(0, 20).map((comment, i) => {
                const sentiment = String(comment.sentiment || "");
                const sentimentColor =
                  sentiment === "positive"
                    ? "text-[#059669] bg-[#ecfdf5] border-[#a7f3d0]"
                    : sentiment === "negative"
                      ? "text-[#dc2626] bg-[#fef2f2] border-[#fecaca]"
                      : "text-soft bg-[#f8f6fa] border-line";
                return (
                  <div key={String(comment.id ?? i)} className="rounded-card border border-line bg-white px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-soft">{rv(comment.date, t.noDate)}</span>
                      <span className={`rounded-pill border px-2 py-0.5 text-[10px] font-semibold ${sentimentColor}`}>
                        {sentiment || t.noSentiment}
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
                      {rv(comment.content, "")}
                    </p>
                  </div>
                );
              })
            ) : (
              <div className="rounded-card border border-dashed border-line bg-[#fdfcfe] px-5 py-8 text-center text-sm text-soft">
                {t.noReviews}
              </div>
            )}
          </div>
        </section>
      </PageTabsContent>
    </PageTabs>
  );
}
