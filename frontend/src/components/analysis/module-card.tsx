"use client";

import { useState, type ReactNode } from "react";
import { Download, Languages, Loader2 } from "lucide-react";
import * as XLSX from "xlsx";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { exportModuleXlsx } from "@/lib/api/browser";
import { useTranslatedContent } from "@/hooks/useTranslatedContent";
import { InlineActionButton } from "@/components/analysis/inline-action-button";
import { DownloadTagButton } from "@/components/analysis/download-tag-button";
import {
  customerLabelOccurrences,
  isFrontstageCustomerLabelOccurrence,
  isVerifiedSourceReviewOccurrence,
  rowImpactReviewShare,
  rowMentionShare,
  rowRepresentativeEvidence,
  rowReviewCount,
} from "@/lib/customer-labels";

type SessionInfo = {
  product_ref_id?: number | null;
  product_id: string;
  version: string;
  custom_title?: string | null;
  auto_title?: string | null;
};

type IssueMeta = {
  specificIssue?: string | null;
  canonicalIssueKey?: string | null;
  customerHighlight?: string | null;
  canonicalHighlightKey?: string | null;
  aspectKey?: string | null;
  aspectKeys?: string[] | null;
  dimension?: string | null;
  subCategory?: string | null;
};

type ModuleCardProps = {
  sessionId: number;
  moduleKey: string;
  moduleData: Record<string, unknown>;
  comments?: Array<Record<string, unknown>>;
  locale?: string;
  session?: SessionInfo;
  showAction?: boolean;
  children: ReactNode;
};

export function ModuleCard({ sessionId, moduleKey, moduleData, comments, locale, session, showAction, children }: ModuleCardProps) {
  const tCommon = useTranslations("common");
  const [exporting, setExporting] = useState(false);

  const {
    translatedData,
    isLoading: translating,
    isFallback,
    needsTranslation,
    showTranslation,
    toggleTranslation,
  } = useTranslatedContent({
    moduleKey,
    sessionId,
    content: moduleData,
  });

  const showTranslatedContent =
    needsTranslation && showTranslation && translatedData != null && !isFallback;

  async function handleExport() {
    setExporting(true);
    try {
      let blob: Blob;
      if (sessionId > 0) {
        blob = await exportModuleXlsx(sessionId, moduleKey, locale);
      } else {
        blob = buildClientXlsx(moduleKey, comments || [], locale || "zh");
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `analysis_${sessionId || "aggregated"}_${moduleKey}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // silently fail
    } finally {
      setExporting(false);
    }
  }

  return (
    <section className="relative rounded-shell border border-line bg-white p-6 shadow-card">
      {/* Toolbar */}
      <div className="absolute right-4 top-4 flex items-center gap-1.5">
        {needsTranslation && translatedData != null && !translating && (
          <Button
            variant="outline"
            size="sm"
            onClick={toggleTranslation}
            className="h-7 gap-1 px-2.5 text-[11px]"
          >
            <Languages className="h-3 w-3" />
            {showTranslation ? tCommon("showOriginal") : tCommon("translate")}
          </Button>
        )}
        {needsTranslation && translating && (
          <span className="flex items-center gap-1 text-[11px] text-soft">
            <Loader2 className="h-3 w-3 animate-spin" />
            {tCommon("translating")}
          </span>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          disabled={exporting}
          className="h-7 gap-1 px-2.5 text-[11px]"
        >
          {exporting ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Download className="h-3 w-3" />
          )}
          XLSX
        </Button>
      </div>

      {/* Content */}
      <div className="pt-8">
        {showTranslatedContent ? (
          <TranslatedView
            data={translatedData!}
            originalData={moduleData}
            moduleKey={moduleKey}
            sessionId={sessionId}
            session={session}
            comments={comments}
            locale={locale}
            showAction={showAction}
          />
        ) : (
          children
        )}
      </div>

      {/* AI Transparency Label */}
      <p className="mt-4 border-t border-line pt-3 text-center text-[10px] text-soft/70">
        {tCommon("aiDisclaimer")}
      </p>
    </section>
  );
}

function issueLabel(row: Record<string, unknown>, fallback = ""): string {
  return String(row.specific_issue || row.tag || row.label || fallback);
}

function issueDimension(row: Record<string, unknown>): string {
  return String(row.dimension || row.aspect_label || "");
}

function issueAspectKeys(row: Record<string, unknown>): string[] {
  const raw = Array.isArray(row.aspect_keys)
    ? row.aspect_keys
    : String(row.aspect_keys || "")
        .split(",")
        .map((item) => item.trim());
  const keys = raw.map((item) => String(item || "").trim()).filter(Boolean);
  const primary = String(row.aspect_key || "").trim();
  if (primary && !keys.includes(primary)) {
    keys.unshift(primary);
  }
  return keys;
}

function issueMetaFromRow(row: Record<string, unknown> | undefined, fallbackIssue = ""): IssueMeta {
  const source = row || {};
  const aspectKeys = issueAspectKeys(source);
  return {
    specificIssue: issueLabel(source, fallbackIssue) || fallbackIssue || null,
    canonicalIssueKey: String(source.canonical_issue_key || "") || null,
    aspectKey: aspectKeys[0] || String(source.aspect_key || "") || null,
    aspectKeys: aspectKeys.length > 0 ? aspectKeys : null,
    dimension: issueDimension(source) || null,
    subCategory: String(source.sub_category || "") || null,
  };
}

function highlightMetaFromRow(row: Record<string, unknown> | undefined, fallbackHighlight = ""): IssueMeta {
  const source = row || {};
  const aspectKeys = issueAspectKeys(source);
  return {
    customerHighlight: String(source.customer_highlight || source.tag || source.label || fallbackHighlight) || fallbackHighlight || null,
    canonicalHighlightKey: String(source.canonical_highlight_key || "") || null,
    aspectKey: aspectKeys[0] || String(source.aspect_key || "") || null,
    aspectKeys: aspectKeys.length > 0 ? aspectKeys : null,
    dimension: issueDimension(source) || null,
    subCategory: String(source.sub_category || "") || null,
  };
}

function buildClientXlsx(
  moduleKey: string,
  comments: Array<Record<string, unknown>>,
  locale: string,
): Blob {
  const wb = XLSX.utils.book_new();
  const labelHeaders =
    locale === "zh"
      ? ["排名", "客户标签", "Mention Count", "Mention Share", "Review Count", "Impact Review Share", "Representative Evidence", "Canonical Label Key", "内部维度", "Aspect Key", "Confidence", "Evidence Verified", "Cluster Propagated"]
      : ["Rank", "Customer Label", "Mention Count", "Mention Share", "Review Count", "Impact Review Share", "Representative Evidence", "Canonical Label Key", "Internal Aspect", "Aspect Key", "Confidence", "Evidence Verified", "Cluster Propagated"];
  const issueHeaders =
    locale === "zh"
      ? ["排名", "客户痛点", "Mention Count", "Mention Share", "Review Count", "Impact Review Share", "Representative Evidence", "Canonical Issue Key", "内部维度", "Aspect Key", "Confidence", "Evidence Verified", "Cluster Propagated"]
      : ["Rank", "Customer Issue", "Mention Count", "Mention Share", "Review Count", "Impact Review Share", "Representative Evidence", "Canonical Issue Key", "Internal Aspect", "Aspect Key", "Confidence", "Evidence Verified", "Cluster Propagated"];

  function formatPct(value: number) {
    return `${value.toFixed(1)}%`;
  }

  function buildCustomerLabelTop10(labelType: "issue" | "highlight") {
    const groups = new Map<string, {
      label: string;
      canonicalLabelKey: string;
      aspectKeys: string[];
      dimensions: string[];
      evidenceSpans: string[];
      confidence: string;
      mentionCount: number;
      evidenceVerified: boolean;
      clusterPropagated: boolean;
    }>();

    for (const [index, comment] of comments.entries()) {
      const commentId = comment.id ?? `row-${index}`;
      const counted = new Set<string>();
      for (const occurrence of customerLabelOccurrences(comment, labelType, locale)) {
        if (!isFrontstageCustomerLabelOccurrence(occurrence)) continue;
        if (!occurrence.canonicalLabelKey) continue;
        const key = `${occurrence.subCategory}::${occurrence.canonicalLabelKey}`;
        const group = groups.get(key) || {
          label: occurrence.label,
          canonicalLabelKey: occurrence.canonicalLabelKey,
          aspectKeys: [],
          dimensions: [],
          evidenceSpans: [],
          confidence: occurrence.confidence || "low",
          mentionCount: 0,
          evidenceVerified: false,
          clusterPropagated: false,
        };
        if (!counted.has(`${commentId}::${key}`)) {
          group.mentionCount += 1;
          counted.add(`${commentId}::${key}`);
        }
        if (occurrence.aspectKey && !group.aspectKeys.includes(occurrence.aspectKey)) {
          group.aspectKeys.push(occurrence.aspectKey);
        }
        if (occurrence.dimension && !group.dimensions.includes(occurrence.dimension)) {
          group.dimensions.push(occurrence.dimension);
        }
        if (isVerifiedSourceReviewOccurrence(occurrence) && group.evidenceSpans.length < 20) {
          group.evidenceSpans.push(occurrence.evidenceSpan);
          group.evidenceVerified = true;
        }
        if (occurrence.confidence === "high") {
          group.confidence = "high";
        }
        groups.set(key, group);
      }
    }

    const totalMentions = Array.from(groups.values()).reduce((sum, group) => sum + group.mentionCount, 0);
    const totalReviews = comments.length || 1;
    return Array.from(groups.values())
      .sort((a, b) => b.mentionCount - a.mentionCount || a.label.localeCompare(b.label))
      .slice(0, 10)
      .map((group, i) => {
        const mentionShare = totalMentions > 0 ? (group.mentionCount / totalMentions) * 100 : 0;
        const impactShare = (group.mentionCount / totalReviews) * 100;
        return [
          i + 1,
          group.label,
          group.mentionCount,
          formatPct(mentionShare),
          group.mentionCount,
          formatPct(impactShare),
          group.evidenceSpans.join(" | "),
          group.canonicalLabelKey,
          group.dimensions.join(", "),
          group.aspectKeys.join(", "),
          group.confidence,
          group.evidenceVerified ? "true" : "false",
          group.clusterPropagated ? "true" : "false",
        ];
      });
  }

  if (moduleKey === "user_experience") {
    const posData = [labelHeaders, ...buildCustomerLabelTop10("highlight")];
    const wsPos = XLSX.utils.aoa_to_sheet(posData);
    XLSX.utils.book_append_sheet(wb, wsPos, locale === "zh" ? "正向反馈 TOP10" : "Positive Feedback TOP10");
    const negData = [issueHeaders, ...buildCustomerLabelTop10("issue")];
    const wsNeg = XLSX.utils.aoa_to_sheet(negData);
    XLSX.utils.book_append_sheet(wb, wsNeg, locale === "zh" ? "负向反馈 TOP10" : "Negative Feedback TOP10");
  } else if (moduleKey === "purchase_motives") {
    const data = [labelHeaders, ...buildCustomerLabelTop10("highlight")];
    const ws = XLSX.utils.aoa_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, locale === "zh" ? "消费动机" : "Purchase Motives");
  } else if (moduleKey === "unmet_needs") {
    const data = [issueHeaders, ...buildCustomerLabelTop10("issue")];
    const ws = XLSX.utils.aoa_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, locale === "zh" ? "未满足的需求" : "Unmet Needs");
  } else if (moduleKey === "consumer_profile") {
    const posData = [labelHeaders, ...buildCustomerLabelTop10("highlight")];
    const wsPos = XLSX.utils.aoa_to_sheet(posData);
    XLSX.utils.book_append_sheet(wb, wsPos, locale === "zh" ? "亮点标签 TOP10" : "Highlight Tags TOP10");
    const negData = [issueHeaders, ...buildCustomerLabelTop10("issue")];
    const wsNeg = XLSX.utils.aoa_to_sheet(negData);
    XLSX.utils.book_append_sheet(wb, wsNeg, locale === "zh" ? "问题标签 TOP10" : "Issue Tags TOP10");
  } else {
    const ws = XLSX.utils.aoa_to_sheet([labelHeaders]);
    XLSX.utils.book_append_sheet(wb, ws, moduleKey);
  }

  // AI Transparency disclaimer row (California AI Transparency Act AB 2013)
  const aiNote =
    locale === "zh"
      ? "AI 生成分析 · 基于 OpenAI GPT-4o-mini"
      : "Analysis powered by AI (OpenAI GPT-4o-mini)";
  const wsNote = XLSX.utils.aoa_to_sheet([[], [aiNote]]);
  XLSX.utils.book_append_sheet(wb, wsNote, locale === "zh" ? "AI 标注" : "AI Notice");

  const buf = XLSX.write(wb, { type: "array", bookType: "xlsx" });
  return new Blob([buf], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

function TranslatedView({
  data,
  originalData,
  moduleKey,
  sessionId,
  session,
  comments,
  locale,
  showAction,
}: {
  data: Record<string, unknown>;
  originalData: Record<string, unknown>;
  moduleKey: string;
  sessionId: number;
  session?: SessionInfo;
  comments?: Array<Record<string, unknown>>;
  locale?: string;
  showAction?: boolean;
}) {
  const t = useTranslations("analysis");
  const summary = String(data.summary || "");
  const rows = Array.isArray(data.rows) ? data.rows : [];
  const positive = Array.isArray(data.positive) ? data.positive : [];
  const negative = Array.isArray(data.negative) ? data.negative : [];
  const evidence = Array.isArray(data.evidence) ? data.evidence : [];

  const origPositive = Array.isArray(originalData.positive) ? originalData.positive as Record<string, unknown>[] : [];
  const origNegative = Array.isArray(originalData.negative) ? originalData.negative as Record<string, unknown>[] : [];
  const origRows = Array.isArray(originalData.rows) ? originalData.rows as Record<string, unknown>[] : [];

  function renderRowButtons(
    tag: string,
    pct: number,
    reason: string,
    tagSource: "highlight_tag" | "issue_tag",
    canAction: boolean,
    meta: IssueMeta = {},
    mentionShare = pct,
    impactReviewShare = pct,
  ) {
    return (
      <div className="mt-2 flex items-center gap-1.5">
        {comments && (
          <DownloadTagButton
            tag={tag}
            comments={comments}
            tagSource={tagSource}
            locale={locale || "zh"}
            specificIssue={meta.specificIssue}
            canonicalIssueKey={meta.canonicalIssueKey}
            customerHighlight={meta.customerHighlight}
            canonicalHighlightKey={meta.canonicalHighlightKey}
            aspectKey={meta.aspectKey}
            aspectKeys={meta.aspectKeys}
            dimension={meta.dimension}
            subCategory={meta.subCategory}
            mentionShare={mentionShare}
            impactReviewShare={impactReviewShare}
          />
        )}
        {canAction && session && sessionId > 0 && (
          <InlineActionButton
            sessionId={sessionId}
            productId={session.product_ref_id}
            sourceProductId={session.product_id}
            sourceVersion={session.version}
            tag={tag}
            pct={pct}
            reason={reason}
            specificIssue={meta.specificIssue}
            canonicalIssueKey={meta.canonicalIssueKey}
            aspectKey={meta.aspectKey}
            dimension={meta.dimension}
          />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {summary && <p className="text-sm leading-7 text-ink">{summary}</p>}

      {moduleKey === "user_experience" && (
        <div className="flex flex-col gap-4">
          {positive.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-[#059669]">{t("positiveFeedback")}</div>
              {positive.map((row: Record<string, unknown>, i: number) => {
                const origRow = origPositive[i];
                const metricRow = origRow || row;
                const tag = String(row.customer_highlight || row.tag || "");
                const origTag = String(origRow?.customer_highlight || origRow?.tag || tag);
                const meta = highlightMetaFromRow(origRow, origTag);
                const pct = rowMentionShare(metricRow);
                const impactShare = rowImpactReviewShare(metricRow, comments?.length || 0);
                const reviewCount = rowReviewCount(metricRow);
                const evidenceRows = rowRepresentativeEvidence(metricRow);
                const reason = String(row.reason || "");
                return (
                  <div key={i} className="rounded-card border border-line bg-white p-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-soft">{i + 1}</span>
                      <span className="text-sm font-semibold text-ink">{tag}</span>
                      <span className="text-xs text-soft">{pct.toFixed(1)}%</span>
                      <span className="text-xs text-soft">{reviewCount} / {comments?.length || 0} ({impactShare.toFixed(1)}%)</span>
                    </div>
                    {evidenceRows.length > 0 ? (
                      <p className="mt-1 text-xs text-soft italic">
                        &ldquo;{evidenceRows[0].evidenceSpan}&rdquo;
                      </p>
                    ) : null}
                    {renderRowButtons(origTag, pct, reason, "highlight_tag", false, meta, pct, impactShare)}
                  </div>
                );
              })}
            </div>
          )}
          {negative.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-[#dc2626]">{t("negativeFeedback")}</div>
              {negative.map((row: Record<string, unknown>, i: number) => {
                const origRow = origNegative[i];
                const metricRow = origRow || row;
                const tag = issueLabel(row, issueLabel(origRow || {}, ""));
                const origTag = issueLabel(origRow || {}, tag);
                const meta = issueMetaFromRow(origRow, origTag);
                const dimension = issueDimension(row) || meta.dimension || "";
                const pct = rowMentionShare(metricRow);
                const impactShare = rowImpactReviewShare(metricRow, comments?.length || 0);
                const reviewCount = rowReviewCount(metricRow);
                const evidenceRows = rowRepresentativeEvidence(metricRow);
                const reason = String(row.reason || "");
                return (
                  <div key={i} className="rounded-card border border-line bg-white p-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-soft">{i + 1}</span>
                      <span className="text-sm font-semibold text-ink">{tag}</span>
                      <span className="text-xs text-soft">{pct.toFixed(1)}%</span>
                      <span className="text-xs text-soft">{reviewCount} / {comments?.length || 0} ({impactShare.toFixed(1)}%)</span>
                    </div>
                    {evidenceRows.length > 0 ? (
                      <p className="mt-1 text-xs text-soft italic">
                        &ldquo;{evidenceRows[0].evidenceSpan}&rdquo;
                      </p>
                    ) : null}
                    {renderRowButtons(origTag, pct, reason, "issue_tag", !!showAction, {
                      ...meta,
                      dimension: meta.dimension || dimension,
                    }, pct, impactShare)}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {rows.length > 0 && moduleKey !== "user_experience" && (
        <div className="space-y-2">
          {rows.map((row: Record<string, unknown>, i: number) => {
            const origRow = origRows[i];
            const metricRow = origRow || row;
            const pct = rowMentionShare(metricRow);
            const impactShare = rowImpactReviewShare(metricRow, comments?.length || 0);
            const reviewCount = rowReviewCount(metricRow);
            const evidenceRows = rowRepresentativeEvidence(metricRow);
            const reason = String(row.reason || row.detail || "");
            const tagSource: "highlight_tag" | "issue_tag" =
              moduleKey === "unmet_needs" ? "issue_tag" : "highlight_tag";
            const canAction = moduleKey === "unmet_needs" && !!showAction;
            const isSpecificIssue = moduleKey === "unmet_needs";
            const tag = isSpecificIssue
              ? issueLabel(row, issueLabel(origRow || {}, ""))
              : String(row.customer_highlight || row.tag || row.label || "");
            const origTag = isSpecificIssue
              ? issueLabel(origRow || {}, tag)
              : String(origRow?.customer_highlight || origRow?.tag || origRow?.label || tag);
            const meta = isSpecificIssue ? issueMetaFromRow(origRow, origTag) : highlightMetaFromRow(origRow, origTag);
            const dimension = isSpecificIssue ? issueDimension(row) || meta.dimension || "" : "";
            return (
              <div key={i} className="rounded-card border border-line bg-[#faf8fb] px-4 py-3">
                <div className="flex items-center gap-2">
                  {tag ? (
                    <span className="text-sm font-semibold text-ink">{tag}</span>
                  ) : null}
                  <span className="text-xs text-soft">{pct.toFixed(1)}%</span>
                  <span className="text-xs text-soft">{reviewCount} / {comments?.length || 0} ({impactShare.toFixed(1)}%)</span>
                </div>
                {evidenceRows.length > 0 ? (
                  <p className="mt-1 text-xs leading-5 text-soft">&ldquo;{evidenceRows[0].evidenceSpan}&rdquo;</p>
                ) : null}
                {renderRowButtons(origTag, pct, reason, tagSource, canAction, {
                  ...meta,
                  dimension: meta.dimension || dimension,
                }, pct, impactShare)}
              </div>
            );
          })}
        </div>
      )}

      {evidence.length > 0 && (
        <div className="rounded-card border border-dashed border-line bg-[#fdfcfe] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.08em] text-soft">{t("moduleCardEvidence")}</div>
          <div className="mt-2 space-y-1.5">
            {evidence.map((quote: unknown, i: number) => (
              <p key={i} className="text-xs italic leading-5 text-soft">&ldquo;{String(quote)}&rdquo;</p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
