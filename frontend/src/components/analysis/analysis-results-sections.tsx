"use client";

import { useState, type ReactNode } from "react";
import {
  ThumbsUp,
  ThumbsDown,
  ChevronRight,
} from "lucide-react";

import { ModuleCard } from "@/components/analysis/module-card";
import { InlineActionButton } from "@/components/analysis/inline-action-button";
import { CreateActionPanel } from "@/components/analysis/create-action-panel";
import { SectionAnchorNav } from "@/components/analysis/section-anchor-nav";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
  filterBarSlot?: ReactNode;
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

function truncate(text: string, max = 140): string {
  if (!text) return "";
  return text.length > max ? text.slice(0, max) + "…" : text;
}

function extractQuotes(row: RowItem): string[] {
  const arr = row.representative_comments;
  if (Array.isArray(arr) && arr.length > 0) {
    return arr
      .map((q) => String(q || "").trim())
      .filter(Boolean)
      .slice(0, 5)
      .map((q) => truncate(q, 140));
  }
  const single = String(row.reason || row.detail || "").trim();
  if (single && single !== "No representative comment found.") {
    return [truncate(single, 140)];
  }
  return [];
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

  const limited = items.slice(0, 10);

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
        {limited.map((row, i) => {
          const tag = String(row.tag || row.label || `#${i + 1}`);
          const pct = Number(row.pct || 0);
          const quotes = extractQuotes(row);
          const reasonForAction = String(row.reason || row.detail || "");
          return (
            <TableRow key={`${variant}-${i}`} className="group align-top">
              <TableCell className="text-center text-xs font-bold text-soft">
                {i + 1}
              </TableCell>
              <TableCell className="text-sm font-semibold text-ink">
                {tag}
              </TableCell>
              <TableCell>
                <PctBar pct={pct} color={barColor} />
              </TableCell>
              <TableCell className="text-xs leading-5 text-soft">
                {quotes.length > 0 ? (
                  <ul className="space-y-1.5">
                    {quotes.map((q, qi) => (
                      <li key={qi} className="flex gap-1.5">
                        <span className="text-soft/60">•</span>
                        <span>{q}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  "—"
                )}
              </TableCell>
              {showAction && sessionId > 0 && (
                <TableCell>
                  <InlineActionButton
                    sessionId={sessionId}
                    productId={session.product_ref_id}
                    sourceProductId={session.product_id}
                    sourceVersion={session.version}
                    tag={tag}
                    pct={pct}
                    reason={reasonForAction}
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

function SectionHeading({ id, title, desc }: { id: string; title: string; desc?: string }) {
  return (
    <div id={id} className="scroll-mt-32">
      <h2 className="font-heading text-lg font-extrabold tracking-[-0.02em] text-ink">
        {title}
      </h2>
      {desc && <p className="mt-1 text-xs text-soft">{desc}</p>}
    </div>
  );
}

const REVIEWS_PAGE_SIZE = 20;

export function AnalysisResultsSections({
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
  filterBarSlot,
  t,
}: Props) {
  const [reviewsShown, setReviewsShown] = useState(REVIEWS_PAGE_SIZE);
  const canShowActions = sessionId > 0;
  const sections = [
    { id: "profile", label: t.moduleConsumerProfile || "用户画像" },
    { id: "experience", label: t.moduleUserExperience || "用户体验" },
    { id: "motives", label: t.modulePurchaseMotives || "消费动机" },
    { id: "needs", label: t.moduleUnmetNeeds || "未满足的需求" },
    { id: "recommendations", label: t.moduleRecommendations || "综合建议" },
    ...(canShowActions ? [{ id: "actions", label: t.tabCreateAction || "创建行动" }] : []),
    { id: "reviews", label: t.rawReviews || "评论原文" },
  ];

  const positiveTop = Math.min(userExperience.positive.length, 10);
  const negativeTop = Math.min(userExperience.negative.length, 10);

  return (
    <div className="flex flex-col gap-4">
      {filterBarSlot}
      <SectionAnchorNav sections={sections} offsetTop={130} />

      {/* Hero: 概览（无标题、无锚点） */}
      <section>{overviewSlot}</section>

      {/* Section: 用户画像 */}
      <section className="flex flex-col gap-3">
        <SectionHeading
          id="profile"
          title={t.moduleConsumerProfile || "用户画像"}
          desc={t.moduleConsumerProfileDesc}
        />
        <ModuleCard
          sessionId={sessionId}
          moduleKey="consumer_profile"
          moduleData={(modules.consumer_profile as Record<string, unknown>) || {}}
        >
          <p className="text-sm leading-7 text-ink">{consumerProfile.summary}</p>
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
      </section>

      {/* Section: 用户体验 */}
      <section className="flex flex-col gap-3">
        <SectionHeading
          id="experience"
          title={t.moduleUserExperience || "用户体验"}
          desc={t.moduleUserExperienceDesc}
        />
        <ModuleCard
          sessionId={sessionId}
          moduleKey="user_experience"
          moduleData={(modules.user_experience as Record<string, unknown>) || {}}
        >
          <div className="flex flex-col gap-6">
            <div>
              <div className="mb-3 flex items-center gap-2">
                <ThumbsUp className="h-4 w-4 text-[#059669]" />
                <span className="text-sm font-semibold text-[#059669]">
                  {t.positiveFeedback} TOP {positiveTop}
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
                  {t.negativeFeedback} TOP {negativeTop}
                </span>
              </div>
              <TagTable
                items={userExperience.negative}
                variant="negative"
                sessionId={sessionId}
                session={session}
                showAction={canShowActions}
              />
              {userExperience.negative.length === 0 && (
                <p className="text-sm text-soft">{t.noNegative}</p>
              )}
            </div>
          </div>
        </ModuleCard>
      </section>

      {/* Section: 消费动机 */}
      <section className="flex flex-col gap-3">
        <SectionHeading
          id="motives"
          title={t.modulePurchaseMotives || "消费动机"}
          desc={t.modulePurchaseMotivesDesc}
        />
        <ModuleCard
          sessionId={sessionId}
          moduleKey="purchase_motives"
          moduleData={(modules.purchase_motives as Record<string, unknown>) || {}}
        >
          <p className="text-sm leading-7 text-ink">{purchaseMotives.summary}</p>
          <div className="mt-4">
            <TagTable
              items={purchaseMotives.rows}
              variant="positive"
              sessionId={sessionId}
              session={session}
            />
          </div>
        </ModuleCard>
      </section>

      {/* Section: 未满足的需求 */}
      <section className="flex flex-col gap-3">
        <SectionHeading
          id="needs"
          title={t.moduleUnmetNeeds || "未满足的需求"}
          desc={t.moduleUnmetNeedsDesc}
        />
        <ModuleCard
          sessionId={sessionId}
          moduleKey="unmet_needs"
          moduleData={(modules.unmet_needs as Record<string, unknown>) || {}}
        >
          <p className="text-sm leading-7 text-ink">{unmetNeeds.summary}</p>
          <div className="mt-4">
            <TagTable
              items={unmetNeeds.rows}
              variant="negative"
              sessionId={sessionId}
              session={session}
              showAction={canShowActions}
            />
          </div>
        </ModuleCard>
      </section>

      {/* Section: 综合建议 */}
      <section className="flex flex-col gap-3">
        <SectionHeading
          id="recommendations"
          title={t.moduleRecommendations || "综合建议"}
          desc={t.moduleRecommendationsDesc}
        />
        <ModuleCard
          sessionId={sessionId}
          moduleKey="recommendations"
          moduleData={(modules.recommendations as Record<string, unknown>) || {}}
        >
          <p className="text-sm leading-7 text-ink">{recommendations.summary}</p>
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
      </section>

      {/* Section: 创建行动 */}
      {canShowActions && (
        <section className="flex flex-col gap-3">
          <SectionHeading id="actions" title={t.tabCreateAction || "创建行动"} />
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
        </section>
      )}

      {/* Section: 评论原文 */}
      <section className="flex flex-col gap-3">
        <SectionHeading id="reviews" title={t.rawReviews || "评论原文"} />
        <div className="rounded-shell border border-line bg-white p-5 shadow-card">
          <div className="space-y-2">
            {comments.length > 0 ? (
              <>
                {comments.slice(0, reviewsShown).map((comment, i) => {
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
                })}
                {reviewsShown < comments.length && (
                  <div className="flex justify-center pt-2">
                    <button
                      type="button"
                      onClick={() => setReviewsShown((n) => n + REVIEWS_PAGE_SIZE)}
                      className="rounded-pill border border-line bg-white px-4 py-2 text-xs font-semibold text-ink shadow-sm hover:bg-[#faf8fb]"
                    >
                      显示更多（剩余 {comments.length - reviewsShown}）
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-card border border-dashed border-line bg-[#fdfcfe] px-5 py-8 text-center text-sm text-soft">
                {t.noReviews}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
