"use client";

import { useState, type ReactNode } from "react";
import {
  ThumbsUp,
  ThumbsDown,
  ChevronRight,
  Download,
  Info,
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
import { aspectLabel } from "@/lib/aspect-labels";
import {
  customerLabelOccurrences,
  customerTagText,
  isVerifiedSourceReviewOccurrence,
  rowImpactReviewShare,
  rowMentionCount,
  rowMentionShare,
  rowRepresentativeEvidence,
  rowReviewCount,
  rowUsesLegacyStats,
  type CustomerLabelEvidence,
} from "@/lib/customer-labels";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

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
  aspectKey?: string | null;
  canonicalIssueKey?: string | null;
  specificIssue?: string | null;
  dimension?: string | null;
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

function joinCustomerLabelField(
  comment: Record<string, unknown>,
  type: "issue" | "highlight",
  field: string,
  locale: string,
  displayOnly = true,
): string {
  return customerLabelOccurrences(comment, type, locale)
    .filter((occurrence) => !displayOnly || isVerifiedSourceReviewOccurrence(occurrence))
    .map((occurrence) => {
      if (field === "label") return occurrence.label;
      if (field === "canonical_label_key") return occurrence.canonicalLabelKey;
      if (field === "key" || field === "aspect_key") return occurrence.aspectKey;
      if (field === "evidence_span") return occurrence.evidenceSpan;
      if (field === "confidence") return occurrence.confidence;
      return "";
    })
    .filter(Boolean)
    .join(", ");
}

function joinCustomerLabelEvidenceVerified(
  comment: Record<string, unknown>,
  type: "issue" | "highlight",
  locale: string,
  displayOnly = true,
): string {
  return customerLabelOccurrences(comment, type, locale)
    .filter((occurrence) => !displayOnly || isVerifiedSourceReviewOccurrence(occurrence))
    .map((occurrence) => (isVerifiedSourceReviewOccurrence(occurrence) ? "true" : "false"))
    .join(", ");
}

function joinCustomerLabelClusterPropagated(
  comment: Record<string, unknown>,
  type: "issue" | "highlight",
  locale: string,
  displayOnly = true,
): string {
  return customerLabelOccurrences(comment, type, locale)
    .filter((occurrence) => !displayOnly || isVerifiedSourceReviewOccurrence(occurrence))
    .map((occurrence) => (occurrence.clusterPropagated ? "true" : "false"))
    .join(", ");
}

function joinCustomerLabelDimension(
  comment: Record<string, unknown>,
  type: "issue" | "highlight",
  locale: string,
  displayOnly = true,
): string {
  return customerLabelOccurrences(comment, type, locale)
    .filter((occurrence) => !displayOnly || isVerifiedSourceReviewOccurrence(occurrence))
    .map((occurrence) => occurrence.dimension || (occurrence.aspectKey ? aspectLabel(occurrence.aspectKey, locale) : ""))
    .filter(Boolean)
    .join(", ");
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
      ? ["序号", "评论内容", "评分", "日期", "评论者", "来源", "情感", "分类", "优先级", "分析理由", "改进建议", "问题标签", "亮点标签", "客户痛点", "Canonical Issue Key", "内部维度", "Aspect Key", "Evidence Span", "Issue Confidence", "Evidence Verified", "Cluster Propagated", "客户亮点", "Canonical Highlight Key", "Highlight 内部维度", "Highlight Aspect Key", "Highlight Evidence Span", "Highlight Confidence", "Highlight Evidence Verified", "Highlight Cluster Propagated", "Audit Customer Issue", "Audit Canonical Issue Key", "Audit 内部维度", "Audit Aspect Key", "Audit Evidence Span", "Audit Issue Confidence", "Audit Evidence Verified", "Audit Cluster Propagated", "Audit Customer Label", "Audit Canonical Highlight Key", "Audit Highlight 内部维度", "Audit Highlight Aspect Key", "Audit Highlight Evidence Span", "Audit Highlight Confidence", "Audit Highlight Evidence Verified", "Audit Highlight Cluster Propagated"]
      : ["No.", "Review", "Rating", "Date", "Reviewer", "Source", "Sentiment", "Category", "Priority", "Reason", "Improvement", "Issue Tags", "Highlight Tags", "Customer Issue", "Canonical Issue Key", "Internal Aspect", "Aspect Key", "Evidence Span", "Issue Confidence", "Evidence Verified", "Cluster Propagated", "Customer Label", "Canonical Highlight Key", "Highlight Internal Aspect", "Highlight Aspect Key", "Highlight Evidence Span", "Highlight Confidence", "Highlight Evidence Verified", "Highlight Cluster Propagated", "Audit Customer Issue", "Audit Canonical Issue Key", "Audit Internal Aspect", "Audit Aspect Key", "Audit Evidence Span", "Audit Issue Confidence", "Audit Evidence Verified", "Audit Cluster Propagated", "Audit Customer Label", "Audit Canonical Highlight Key", "Audit Highlight Internal Aspect", "Audit Highlight Aspect Key", "Audit Highlight Evidence Span", "Audit Highlight Confidence", "Audit Highlight Evidence Verified", "Audit Highlight Cluster Propagated"];
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
    customerTagText(comment, "issue", locale),
    customerTagText(comment, "highlight", locale),
    joinCustomerLabelField(comment, "issue", "label", locale),
    joinCustomerLabelField(comment, "issue", "canonical_label_key", locale),
    joinCustomerLabelDimension(comment, "issue", locale),
    joinCustomerLabelField(comment, "issue", "key", locale) || joinCustomerLabelField(comment, "issue", "aspect_key", locale),
    joinCustomerLabelField(comment, "issue", "evidence_span", locale),
    joinCustomerLabelField(comment, "issue", "confidence", locale),
    joinCustomerLabelEvidenceVerified(comment, "issue", locale),
    joinCustomerLabelClusterPropagated(comment, "issue", locale),
    joinCustomerLabelField(comment, "highlight", "label", locale),
    joinCustomerLabelField(comment, "highlight", "canonical_label_key", locale),
    joinCustomerLabelDimension(comment, "highlight", locale),
    joinCustomerLabelField(comment, "highlight", "key", locale) || joinCustomerLabelField(comment, "highlight", "aspect_key", locale),
    joinCustomerLabelField(comment, "highlight", "evidence_span", locale),
    joinCustomerLabelField(comment, "highlight", "confidence", locale),
    joinCustomerLabelEvidenceVerified(comment, "highlight", locale),
    joinCustomerLabelClusterPropagated(comment, "highlight", locale),
    joinCustomerLabelField(comment, "issue", "label", locale, false),
    joinCustomerLabelField(comment, "issue", "canonical_label_key", locale, false),
    joinCustomerLabelDimension(comment, "issue", locale, false),
    joinCustomerLabelField(comment, "issue", "key", locale, false) || joinCustomerLabelField(comment, "issue", "aspect_key", locale, false),
    joinCustomerLabelField(comment, "issue", "evidence_span", locale, false),
    joinCustomerLabelField(comment, "issue", "confidence", locale, false),
    joinCustomerLabelEvidenceVerified(comment, "issue", locale, false),
    joinCustomerLabelClusterPropagated(comment, "issue", locale, false),
    joinCustomerLabelField(comment, "highlight", "label", locale, false),
    joinCustomerLabelField(comment, "highlight", "canonical_label_key", locale, false),
    joinCustomerLabelDimension(comment, "highlight", locale, false),
    joinCustomerLabelField(comment, "highlight", "key", locale, false) || joinCustomerLabelField(comment, "highlight", "aspect_key", locale, false),
    joinCustomerLabelField(comment, "highlight", "evidence_span", locale, false),
    joinCustomerLabelField(comment, "highlight", "confidence", locale, false),
    joinCustomerLabelEvidenceVerified(comment, "highlight", locale, false),
    joinCustomerLabelClusterPropagated(comment, "highlight", locale, false),
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
    { wch: 26 },
    { wch: 26 },
    { wch: 24 },
    { wch: 22 },
    { wch: 34 },
    { wch: 18 },
    { wch: 18 },
    { wch: 18 },
    { wch: 26 },
    { wch: 28 },
    { wch: 24 },
    { wch: 22 },
    { wch: 34 },
    { wch: 18 },
    { wch: 22 },
    { wch: 22 },
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

function PctBar({ pct, color, legacy }: { pct: number; color: string; legacy?: boolean }) {
  return (
    <div className="flex items-center gap-2" title={legacy ? "Legacy statistics from an older analysis batch." : undefined}>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-[#f3f0f5]">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-soft">
        {pct.toFixed(1)}%
      </span>
      {legacy ? (
        <span className="rounded-sm bg-[#f7f3ff] px-1 text-[10px] font-semibold text-[#7c3aed]">
          legacy
        </span>
      ) : null}
    </div>
  );
}

function metricText(key: "mention" | "impact" | "legacy", locale: string): string {
  if (key === "mention") {
    return locale.startsWith("zh")
      ? "该标签在同类标签出现次数中的占比。"
      : "Share of this label among all labels of the same type.";
  }
  if (key === "impact") {
    return locale.startsWith("zh")
      ? "命中该标签的评论数，占当前筛选范围总评论数的比例。"
      : "Reviews that hit this label, as a share of all reviews in the current filter scope.";
  }
  return locale.startsWith("zh")
    ? "旧分析批次使用历史统计口径。"
    : "Older analysis batches use the historical statistics definition.";
}

function MetricHeader({
  label,
  tooltip,
}: {
  label: string;
  tooltip: string;
}) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex cursor-help items-center gap-1">
            {label}
            <Info className="h-3 w-3 text-soft/70" />
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs bg-ink text-white">
          {tooltip}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function MetricValueTooltip({
  children,
  legacy,
  locale,
}: {
  children: ReactNode;
  legacy: boolean;
  locale: string;
}) {
  if (!legacy) return <>{children}</>;
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex cursor-help">{children}</span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs bg-ink text-white">
          {metricText("legacy", locale)}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function ImpactReviewMetric({
  row,
  totalReviews,
  locale,
}: {
  row: RowItem;
  totalReviews: number;
  locale: string;
}) {
  const legacy = rowUsesLegacyStats(row);
  const reviewCount = rowReviewCount(row);
  const impactShare = rowImpactReviewShare(row, totalReviews);
  const text = legacy
    ? `${reviewCount} (${impactShare.toFixed(1)}%)`
    : `${reviewCount} / ${totalReviews} (${impactShare.toFixed(1)}%)`;
  return (
    <MetricValueTooltip legacy={legacy} locale={locale}>
      <span className="text-xs tabular-nums text-soft">{text}</span>
    </MetricValueTooltip>
  );
}

function truncate(text: string, max = 140): string {
  if (!text) return "";
  return text.length > max ? text.slice(0, max) + "…" : text;
}

function RepresentativeEvidenceList({
  evidence,
  locale,
  compact = false,
}: {
  evidence: CustomerLabelEvidence[];
  locale: string;
  compact?: boolean;
}) {
  if (evidence.length === 0) {
    return (
      <span className="text-xs text-soft/70">
        {locale.startsWith("zh") ? "暂无可验证代表证据" : "No verified representative evidence"}
      </span>
    );
  }
  return (
    <ul className="space-y-1.5">
      {evidence.slice(0, compact ? 2 : 3).map((item, qi) => (
        <li key={`${item.evidenceSpan}-${qi}`} className="flex gap-1.5">
          <span className="text-soft/60">•</span>
          <details className="min-w-0">
            <summary className="cursor-pointer list-none text-xs leading-5 text-soft">
              &ldquo;{truncate(item.evidenceSpan, compact ? 110 : 140)}&rdquo;
            </summary>
            {item.review ? (
              <p className="mt-1 rounded-card border border-line bg-[#faf8fb] p-2 text-xs leading-5 text-ink">
                {item.review}
              </p>
            ) : null}
          </details>
        </li>
      ))}
    </ul>
  );
}

function rowIssueLabel(row: RowItem, fallback: string): string {
  return String(row.specific_issue || row.tag || row.label || fallback);
}

function rowDimension(row: RowItem): string {
  return String(row.dimension || row.aspect_label || "");
}

function rowAspectKey(row: RowItem): string {
  return String(row.aspect_key || "");
}

function rowAspectKeys(row: RowItem): string[] {
  const values = Array.isArray(row.aspect_keys)
    ? row.aspect_keys
    : String(row.aspect_keys || "")
        .split(",")
        .map((item) => item.trim());
  const keys = values.map((item) => String(item || "").trim()).filter(Boolean);
  const primary = rowAspectKey(row);
  if (primary && !keys.includes(primary)) {
    keys.unshift(primary);
  }
  return keys;
}

function rowCanonicalIssueKey(row: RowItem): string {
  return String(row.canonical_issue_key || "");
}

function rowCanonicalHighlightKey(row: RowItem): string {
  return String(row.canonical_highlight_key || "");
}

function rowSubCategory(row: RowItem): string {
  return String(row.sub_category || "");
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
  const issueMode = variant === "negative" && tagSource === "issue_tag";
  const scopedComments = comments;
  const totalReviews = comments?.length || 0;
  const localeValue = locale || "zh";

  if (issueMode) {
    return (
      <>
        <div className="hidden md:block">
          <Table className="w-full table-fixed">
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-[24%]">{t("specificIssue")}</TableHead>
                <TableHead className="w-40">
                  <MetricHeader label={t("mentionShare")} tooltip={metricText("mention", localeValue)} />
                </TableHead>
                <TableHead className="w-44">
                  <MetricHeader label={t("impactReviews")} tooltip={metricText("impact", localeValue)} />
                </TableHead>
                <TableHead>{t("representativeEvidence")}</TableHead>
                <TableHead className="w-32">{t("action")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {limited.map((row, i) => {
                const tag = rowIssueLabel(row, `#${i + 1}`);
                const mentionShare = rowMentionShare(row);
                const impactShare = rowImpactReviewShare(row, totalReviews);
                const mentionCount = rowMentionCount(row);
                const legacy = rowUsesLegacyStats(row);
                const evidence = rowRepresentativeEvidence(row);
                const dimension = rowDimension(row);
                const aspectKey = rowAspectKey(row);
                const aspectKeys = rowAspectKeys(row);
                const canonicalIssueKey = rowCanonicalIssueKey(row);
                const subCategory = rowSubCategory(row);
                const reasonForAction = String(row.reason || row.detail || "");
                return (
                  <TableRow key={`${variant}-issue-${i}`} className="group align-top">
                    <TableCell className="break-words text-sm font-semibold text-ink">
                      <span className="mr-1.5 text-xs font-bold text-soft">#{i + 1}</span>
                      {tag}
                    </TableCell>
                    <TableCell>
                      <MetricValueTooltip legacy={legacy} locale={localeValue}>
                        <PctBar pct={mentionShare} color={barColor} legacy={legacy} />
                      </MetricValueTooltip>
                      <div className="mt-1 text-[10px] text-soft/70">
                        {t("mentionsCount", { count: mentionCount })}
                      </div>
                    </TableCell>
                    <TableCell>
                      <ImpactReviewMetric row={row} totalReviews={totalReviews} locale={localeValue} />
                    </TableCell>
                    <TableCell className="text-xs leading-5 text-soft">
                      <RepresentativeEvidenceList evidence={evidence} locale={localeValue} />
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col items-start gap-1.5">
                        {scopedComments && (
                          <DownloadTagButton
                            tag={tag}
                            comments={scopedComments}
                            tagSource="issue_tag"
                            locale={localeValue}
                            specificIssue={tag}
                            aspectKey={aspectKey}
                            aspectKeys={aspectKeys}
                            canonicalIssueKey={canonicalIssueKey}
                            dimension={dimension}
                            subCategory={subCategory}
                            mentionShare={mentionShare}
                            impactReviewShare={impactShare}
                          />
                        )}
                        {showAction && sessionId > 0 && (
                          <InlineActionButton
                            sessionId={sessionId}
                            productId={session.product_ref_id}
                            sourceProductId={session.product_id}
                            sourceVersion={session.version}
                            tag={tag}
                            pct={mentionShare}
                            reason={reasonForAction}
                            specificIssue={tag}
                            aspectKey={aspectKey}
                            canonicalIssueKey={canonicalIssueKey}
                            dimension={dimension}
                          />
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
        <div className="grid gap-3 md:hidden">
          {limited.map((row, i) => {
            const tag = rowIssueLabel(row, `#${i + 1}`);
            const mentionShare = rowMentionShare(row);
            const impactShare = rowImpactReviewShare(row, totalReviews);
            const evidence = rowRepresentativeEvidence(row);
            const dimension = rowDimension(row);
            const aspectKey = rowAspectKey(row);
            const aspectKeys = rowAspectKeys(row);
            const canonicalIssueKey = rowCanonicalIssueKey(row);
            const subCategory = rowSubCategory(row);
            const reasonForAction = String(row.reason || row.detail || "");
            return (
              <div key={`${variant}-issue-card-${i}`} className="rounded-card border border-line bg-white p-3">
                <div className="flex items-start gap-2">
                  <span className="shrink-0 text-xs font-bold text-soft">#{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="break-words text-sm font-semibold text-ink">{tag}</div>
                    <div className="mt-1 text-xs text-soft">
                      {t("mentionShare")}: {mentionShare.toFixed(1)}%
                    </div>
                    <div className="text-xs text-soft">
                      {t("impactReviews")}: {rowReviewCount(row)} / {totalReviews} ({impactShare.toFixed(1)}%)
                    </div>
                  </div>
                </div>
                <div className="mt-3">
                  <RepresentativeEvidenceList evidence={evidence} locale={localeValue} compact />
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  {scopedComments && (
                    <DownloadTagButton
                      tag={tag}
                      comments={scopedComments}
                      tagSource="issue_tag"
                      locale={localeValue}
                      specificIssue={tag}
                      aspectKey={aspectKey}
                      aspectKeys={aspectKeys}
                      canonicalIssueKey={canonicalIssueKey}
                      dimension={dimension}
                      subCategory={subCategory}
                      mentionShare={mentionShare}
                      impactReviewShare={impactShare}
                    />
                  )}
                  {showAction && sessionId > 0 && (
                    <InlineActionButton
                      sessionId={sessionId}
                      productId={session.product_ref_id}
                      sourceProductId={session.product_id}
                      sourceVersion={session.version}
                      tag={tag}
                      pct={mentionShare}
                      reason={reasonForAction}
                      specificIssue={tag}
                      aspectKey={aspectKey}
                      canonicalIssueKey={canonicalIssueKey}
                      dimension={dimension}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead className="min-w-[160px]">{t("tag")}</TableHead>
          <TableHead className="w-40">
            <MetricHeader label={t("mentionShare")} tooltip={metricText("mention", localeValue)} />
          </TableHead>
          <TableHead className="w-44">
            <MetricHeader label={t("impactReviews")} tooltip={metricText("impact", localeValue)} />
          </TableHead>
          <TableHead>{t("representativeEvidence")}</TableHead>
          <TableHead className="w-32">{t("download")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {limited.map((row, i) => {
          const tag = String(row.customer_highlight || row.tag || row.label || `#${i + 1}`);
          const mentionShare = rowMentionShare(row);
          const impactShare = rowImpactReviewShare(row, totalReviews);
          const mentionCount = rowMentionCount(row);
          const legacy = rowUsesLegacyStats(row);
          const evidence = rowRepresentativeEvidence(row);
          const reasonForAction = String(row.reason || row.detail || "");
          const aspectKey = rowAspectKey(row);
          const aspectKeys = rowAspectKeys(row);
          const canonicalHighlightKey = rowCanonicalHighlightKey(row);
          const dimension = rowDimension(row);
          return (
            <TableRow key={`${variant}-${i}`} className="group align-top">
              <TableCell className="text-sm font-semibold text-ink">
                <span className="mr-1.5 text-xs font-bold text-soft">#{i + 1}</span>
                {tag}
              </TableCell>
              <TableCell>
                <MetricValueTooltip legacy={legacy} locale={localeValue}>
                  <PctBar pct={mentionShare} color={barColor} legacy={legacy} />
                </MetricValueTooltip>
                <div className="mt-1 text-[10px] text-soft/70">
                  {t("mentionsCount", { count: mentionCount })}
                </div>
              </TableCell>
              <TableCell>
                <ImpactReviewMetric row={row} totalReviews={totalReviews} locale={localeValue} />
              </TableCell>
              <TableCell className="text-xs leading-5 text-soft">
                <RepresentativeEvidenceList evidence={evidence} locale={localeValue} />
              </TableCell>
              <TableCell>
                <div className="flex flex-col items-start gap-1.5">
                  {scopedComments && tagSource && (
                    <DownloadTagButton
                      tag={tag}
                      comments={scopedComments}
                      tagSource={tagSource}
                      locale={localeValue}
                      customerHighlight={tagSource === "highlight_tag" ? tag : null}
                      canonicalHighlightKey={tagSource === "highlight_tag" ? canonicalHighlightKey : null}
                      aspectKey={tagSource === "highlight_tag" ? aspectKey : null}
                      aspectKeys={tagSource === "highlight_tag" ? aspectKeys : null}
                      dimension={tagSource === "highlight_tag" ? dimension : null}
                      mentionShare={mentionShare}
                      impactReviewShare={impactShare}
                    />
                  )}
                  {showAction && sessionId > 0 && (
                    <InlineActionButton
                      sessionId={sessionId}
                      productId={session.product_ref_id}
                      sourceProductId={session.product_id}
                      sourceVersion={session.version}
                      tag={tag}
                      pct={mentionShare}
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
                      const issueTags = customerTagText(comment, "issue", locale);
                      const highlightTags = customerTagText(comment, "highlight", locale);
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
                              {issueTags ? (
                                <span className="rounded-pill border border-[#fecaca] bg-[#fef2f2] px-2 py-0.5 text-[10px] text-[#b91c1c]">
                                  {issueTags}
                                </span>
                              ) : null}
                              {highlightTags ? (
                                <span className="rounded-pill border border-[#a7f3d0] bg-[#ecfdf5] px-2 py-0.5 text-[10px] text-[#047857]">
                                  {highlightTags}
                                </span>
                              ) : null}
                              {!issueTags && !highlightTags ? (
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
