"use client";

import { useState, type ReactNode } from "react";
import {
  ThumbsUp,
  ThumbsDown,
  ChevronRight,
  Download,
  Loader2,
} from "lucide-react";
import { useTranslations } from "next-intl";
import * as XLSX from "xlsx";

import { ModuleCard } from "@/components/analysis/module-card";
import { InlineActionButton } from "@/components/analysis/inline-action-button";
import { DownloadTagButton } from "@/components/analysis/download-tag-button";
import { CreateActionPanel } from "@/components/analysis/create-action-panel";
import { SectionAnchorNav } from "@/components/analysis/section-anchor-nav";
import { Button } from "@/components/ui/button";
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
  locale: string;
};

function rv(value: unknown, fallback = "--"): string {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function reviewBody(comment: Record<string, unknown>): string {
  return rv(comment.content || comment.body || comment.comment, "");
}

function safeFilenamePart(value: string): string {
  return value.trim().replace(/[\\/:*?"<>|]+/g, "_").replace(/\s+/g, "_") || "analysis";
}

function buildRawReviewsXlsx(
  comments: Array<Record<string, unknown>>,
  locale: string,
  session: SessionInfo,
): Blob {
  const wb = XLSX.utils.book_new();
  const headers =
    locale === "zh"
      ? ["序号", "评论内容", "评分", "日期", "评论者", "来源", "情感", "分类", "优先级", "分析理由", "改进建议", "问题标签", "亮点标签"]
      : ["No.", "Review", "Rating", "Date", "Reviewer", "Source", "Sentiment", "Category", "Priority", "Reason", "Improvement", "Issue Tags", "Highlight Tags"];
  const rows = comments.map((comment, index) => [
    index + 1,
    reviewBody(comment),
    comment.rating != null ? Number(comment.rating) : "",
    rv(comment.date, ""),
    rv(comment.reviewer, ""),
    rv(comment.source, ""),
    rv(comment.sentiment, ""),
    rv(comment.category, ""),
    rv(comment.priority, ""),
    rv(comment.reason, ""),
    rv(comment.improvement, ""),
    rv(comment.issue_tag, ""),
    rv(comment.highlight_tag, ""),
  ]);

  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
  ws["!cols"] = [
    { wch: 8 },
    { wch: 64 },
    { wch: 8 },
    { wch: 14 },
    { wch: 20 },
    { wch: 16 },
    { wch: 12 },
    { wch: 16 },
    { wch: 12 },
    { wch: 36 },
    { wch: 36 },
    { wch: 24 },
    { wch: 24 },
  ];
  XLSX.utils.book_append_sheet(wb, ws, locale === "zh" ? "评论原文" : "Raw Reviews");

  const metaHeaders = locale === "zh" ? ["字段", "值"] : ["Field", "Value"];
  const metaRows = [
    [locale === "zh" ? "产品编号" : "Product ID", session.product_id || ""],
    [locale === "zh" ? "版本" : "Version", session.version || ""],
    [locale === "zh" ? "评论数" : "Review Count", comments.length],
    [
      locale === "zh" ? "AI 标注说明" : "AI Notice",
      locale === "zh"
        ? "AI 生成分析 · 基于 OpenAI GPT-4o-mini"
        : "Analysis powered by AI (OpenAI GPT-4o-mini)",
    ],
  ];
  const meta = XLSX.utils.aoa_to_sheet([metaHeaders, ...metaRows]);
  meta["!cols"] = [{ wch: 18 }, { wch: 60 }];
  XLSX.utils.book_append_sheet(wb, meta, locale === "zh" ? "导出信息" : "Export Info");

  const buffer = XLSX.write(wb, { type: "array", bookType: "xlsx" });
  return new Blob([buffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
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

type TagTableProps = {
  items: RowItem[];
  variant: "positive" | "negative" | "neutral";
  sessionId: number;
  session: SessionInfo;
  showAction?: boolean;
  comments?: Array<Record<string, unknown>>;
  tagSource?: "highlight_tag" | "issue_tag";
  locale?: string;
};

function TagTable({
  items,
  variant,
  sessionId,
  session,
  showAction,
  comments,
  tagSource,
  locale,
}: TagTableProps) {
  const t = useTranslations("analysis.table");
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
          <TableHead className="min-w-[120px]">{t("tag")}</TableHead>
          <TableHead className="w-36">{t("mentionPct")}</TableHead>
          <TableHead>{t("reprComments")}</TableHead>
          <TableHead className="w-24" />
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
              <TableCell>
                <div className="flex items-center gap-1.5">
                  {comments && tagSource && (
                    <DownloadTagButton
                      tag={tag}
                      comments={comments}
                      tagSource={tagSource}
                      locale={locale || "zh"}
                    />
                  )}
                  {showAction && sessionId > 0 && (
                    <InlineActionButton
                      sessionId={sessionId}
                      productId={session.product_ref_id}
                      sourceProductId={session.product_id}
                      sourceVersion={session.version}
                      tag={tag}
                      pct={pct}
                      reason={reasonForAction}
                    />
                  )}
                </div>
              </TableCell>
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
  locale,
}: Props) {
  const t = useTranslations("analysis");
  const tTable = useTranslations("analysis.table");
  const [reviewsShown, setReviewsShown] = useState(REVIEWS_PAGE_SIZE);
  const [exportingFull, setExportingFull] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const canShowActions = sessionId > 0;

  async function handleExportRawReviews() {
    if (comments.length === 0) return;
    setExportingFull(true);
    setExportError(null);
    try {
      const blob = buildRawReviewsXlsx(comments, locale, session);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeFilenamePart(session.product_id)}-${safeFilenamePart(session.version)}-raw-reviews.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setExportError(locale === "zh" ? "下载失败，请稍后重试。" : "Download failed. Please try again.");
    } finally {
      setExportingFull(false);
    }
  }

  const sections = [
    { id: "profile", label: t("moduleConsumerProfile") },
    { id: "experience", label: t("moduleUserExperience") },
    { id: "motives", label: t("modulePurchaseMotives") },
    { id: "needs", label: t("moduleUnmetNeeds") },
    { id: "recommendations", label: t("moduleRecommendations") },
    ...(canShowActions ? [{ id: "actions", label: t("tabCreateAction") }] : []),
    { id: "reviews", label: t("rawReviews") },
  ];

  const positiveTop = Math.min(userExperience.positive.length, 10);
  const negativeTop = Math.min(userExperience.negative.length, 10);

  return (
    <div className="flex flex-col gap-4">
      {filterBarSlot}
      <SectionAnchorNav sections={sections} offsetTop={130} />

      {/* AI Transparency Label (California AI Transparency Act AB 2013) */}
      <div className="rounded-card border border-[#e5e0eb] bg-[#faf9fb] px-4 py-2.5 text-center text-[11px] leading-5 text-soft">
        {t("aiDisclaimer")}
      </div>

      {/* Hero: 概览（无标题、无锚点） */}
      <section>{overviewSlot}</section>

      {/* Section: 用户画像 */}
      <section className="flex flex-col gap-3">
        <SectionHeading
          id="profile"
          title={t("moduleConsumerProfile")}
          desc={t("moduleConsumerProfileDesc")}
        />
        <ModuleCard
          sessionId={sessionId}
          moduleKey="consumer_profile"
          moduleData={(modules.consumer_profile as Record<string, unknown>) || {}}
          comments={comments}
          locale={locale}
          session={session}
        >
          <p className="text-sm leading-7 text-ink">{consumerProfile.summary}</p>
          {consumerProfile.rows.length > 0 && (
            <Table className="mt-4">
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-32">{tTable("dimension")}</TableHead>
                  <TableHead>{tTable("detail")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {consumerProfile.rows.map((row, i) => (
                  <TableRow key={`cp-${i}`}>
                    <TableCell className="text-xs font-bold capitalize tracking-wide text-soft">
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
              <div className="text-xs font-semibold uppercase tracking-wide text-soft">{t("evidence")}</div>
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
          title={t("moduleUserExperience")}
          desc={t("moduleUserExperienceDesc")}
        />
        <ModuleCard
          sessionId={sessionId}
          moduleKey="user_experience"
          moduleData={(modules.user_experience as Record<string, unknown>) || {}}
          comments={comments}
          locale={locale}
          session={session}
          showAction={canShowActions}
        >
          <div className="flex flex-col gap-6">
            <div>
              <div className="mb-3 flex items-center gap-2">
                <ThumbsUp className="h-4 w-4 text-[#059669]" />
                <span className="text-sm font-semibold text-[#059669]">
                  {t("positiveFeedback")} TOP {positiveTop}
                </span>
              </div>
              <TagTable
                items={userExperience.positive}
                variant="positive"
                sessionId={sessionId}
                session={session}
                comments={comments}
                tagSource="highlight_tag"
                locale={locale}
              />
              {userExperience.positive.length === 0 && (
                <p className="text-sm text-soft">{t("noPositive")}</p>
              )}
            </div>
            <div>
              <div className="mb-3 flex items-center gap-2">
                <ThumbsDown className="h-4 w-4 text-[#dc2626]" />
                <span className="text-sm font-semibold text-[#dc2626]">
                  {t("negativeFeedback")} TOP {negativeTop}
                </span>
              </div>
              <TagTable
                items={userExperience.negative}
                variant="negative"
                sessionId={sessionId}
                session={session}
                showAction={canShowActions}
                comments={comments}
                tagSource="issue_tag"
                locale={locale}
              />
              {userExperience.negative.length === 0 && (
                <p className="text-sm text-soft">{t("noNegative")}</p>
              )}
            </div>
          </div>
        </ModuleCard>
      </section>

      {/* Section: 消费动机 */}
      <section className="flex flex-col gap-3">
        <SectionHeading
          id="motives"
          title={t("modulePurchaseMotives")}
          desc={t("modulePurchaseMotivesDesc")}
        />
        <ModuleCard
          sessionId={sessionId}
          moduleKey="purchase_motives"
          moduleData={(modules.purchase_motives as Record<string, unknown>) || {}}
          comments={comments}
          locale={locale}
          session={session}
        >
          <p className="text-sm leading-7 text-ink">{purchaseMotives.summary}</p>
          <div className="mt-4">
            <TagTable
              items={purchaseMotives.rows}
              variant="positive"
              sessionId={sessionId}
              session={session}
              comments={comments}
              tagSource="highlight_tag"
              locale={locale}
            />
          </div>
        </ModuleCard>
      </section>

      {/* Section: 未满足的需求 */}
      <section className="flex flex-col gap-3">
        <SectionHeading
          id="needs"
          title={t("moduleUnmetNeeds")}
          desc={t("moduleUnmetNeedsDesc")}
        />
        <ModuleCard
          sessionId={sessionId}
          moduleKey="unmet_needs"
          moduleData={(modules.unmet_needs as Record<string, unknown>) || {}}
          comments={comments}
          locale={locale}
          session={session}
          showAction={canShowActions}
        >
          <p className="text-sm leading-7 text-ink">{unmetNeeds.summary}</p>
          <div className="mt-4">
            <TagTable
              items={unmetNeeds.rows}
              variant="negative"
              sessionId={sessionId}
              session={session}
              showAction={canShowActions}
              comments={comments}
              tagSource="issue_tag"
              locale={locale}
            />
          </div>
        </ModuleCard>
      </section>

      {/* Section: 综合建议 */}
      <section className="flex flex-col gap-3">
        <SectionHeading
          id="recommendations"
          title={t("moduleRecommendations")}
          desc={t("moduleRecommendationsDesc")}
        />
        <ModuleCard
          sessionId={sessionId}
          moduleKey="recommendations"
          moduleData={(modules.recommendations as Record<string, unknown>) || {}}
          comments={comments}
          locale={locale}
          session={session}
        >
          <p className="text-sm leading-7 text-ink">{recommendations.summary}</p>
          <div className="mt-4 space-y-2">
            {recommendations.rows.map((row, i) => (
              <div key={`rec-${i}`} className="flex items-start gap-3 rounded-card border border-line bg-[#faf8fb] px-4 py-3">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#7c3aed] text-xs font-bold text-white">
                  {i + 1}
                </div>
                <p className="min-w-0 flex-1 text-sm leading-6 text-ink">
                  {rv(row.detail || row.reason || row.summary || row.value)}
                </p>
                <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-soft/50" />
              </div>
            ))}
          </div>
        </ModuleCard>
      </section>

      {/* Section: 创建行动 */}
      {canShowActions && (
        <section className="flex flex-col gap-3">
          <SectionHeading id="actions" title={t("tabCreateAction")} />
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
        <SectionHeading id="reviews" title={t("rawReviews")} />
        <div className="rounded-shell border border-line bg-white p-5 shadow-card">
          {comments.length > 0 && (
            <div className="mb-3 flex flex-col items-end gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportRawReviews}
                disabled={exportingFull || comments.length === 0}
                className="h-7 gap-1 px-2.5 text-[11px]"
              >
                {exportingFull ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Download className="h-3 w-3" />
                )}
                XLSX
              </Button>
              {exportError && (
                <p className="text-[11px] text-[#dc2626]">{exportError}</p>
              )}
            </div>
          )}
          <div className="space-y-2">
            {comments.length > 0 ? (
              <>
                <Table className="min-w-[1040px]">
                  <TableHeader>
                    <TableRow className="hover:bg-transparent">
                      <TableHead className="w-28">{tTable("date")}</TableHead>
                      <TableHead className="w-20">{tTable("rating")}</TableHead>
                      <TableHead className="w-32">{tTable("reviewer")}</TableHead>
                      <TableHead className="w-32">{tTable("source")}</TableHead>
                      <TableHead className="w-28">{tTable("sentiment")}</TableHead>
                      <TableHead className="w-56">{tTable("tags")}</TableHead>
                      <TableHead>{tTable("reviewContent")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {comments.slice(0, reviewsShown).map((comment, i) => {
                      const sentiment = String(comment.sentiment || "");
                      const body = reviewBody(comment);
                      const sentimentColor =
                        sentiment === "positive"
                          ? "text-[#059669] bg-[#ecfdf5] border-[#a7f3d0]"
                          : sentiment === "negative"
                            ? "text-[#dc2626] bg-[#fef2f2] border-[#fecaca]"
                            : "text-soft bg-[#f8f6fa] border-line";
                      return (
                        <TableRow key={String(comment.id ?? i)} className="align-top">
                          <TableCell className="text-xs text-soft">
                            {rv(comment.date, t("noDate"))}
                          </TableCell>
                          <TableCell className="text-xs text-ink">
                            {rv(comment.rating)}
                          </TableCell>
                          <TableCell className="max-w-[8rem] truncate text-xs text-ink">
                            {rv(comment.reviewer)}
                          </TableCell>
                          <TableCell className="max-w-[8rem] truncate text-xs text-soft">
                            {rv(comment.source)}
                          </TableCell>
                          <TableCell>
                            <span className={`rounded-pill border px-2 py-0.5 text-[10px] font-semibold ${sentimentColor}`}>
                              {sentiment || t("noSentiment")}
                            </span>
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1.5">
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
                              {!comment.issue_tag && !comment.highlight_tag ? (
                                <span className="text-xs text-soft">--</span>
                              ) : null}
                            </div>
                          </TableCell>
                          <TableCell className="text-sm leading-6 text-ink">
                            <p className="max-w-[460px]" title={body}>
                              {truncate(body, 200)}
                            </p>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
                {reviewsShown < comments.length && (
                  <div className="flex justify-center pt-2">
                    <button
                      type="button"
                      onClick={() => setReviewsShown((n) => n + REVIEWS_PAGE_SIZE)}
                      className="rounded-pill border border-line bg-white px-4 py-2 text-xs font-semibold text-ink shadow-sm hover:bg-[#faf8fb]"
                    >
                      {t("showMore", { count: comments.length - reviewsShown })}
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-card border border-dashed border-line bg-[#fdfcfe] px-5 py-8 text-center text-sm text-soft">
                {t("noReviews")}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
