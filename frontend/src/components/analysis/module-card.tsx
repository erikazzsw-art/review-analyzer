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
import { aspectLabel } from "@/lib/aspect-labels";

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

function parseAspectsPayload(comment: Record<string, unknown>): Record<string, unknown> | null {
  const raw = comment.aspects_json;
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    return raw as Record<string, unknown>;
  }
  if (typeof raw === "string" && raw.trim()) {
    try {
      const parsed = JSON.parse(raw) as unknown;
      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : null;
    } catch {
      return null;
    }
  }
  return null;
}

function getAspects(comment: Record<string, unknown>): Array<Record<string, unknown>> {
  const aspects = parseAspectsPayload(comment)?.aspects;
  return Array.isArray(aspects)
    ? aspects.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    : [];
}

function safeIssueSlug(value: string): string {
  const asciiSlug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  if (asciiSlug) return asciiSlug;
  return value
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "_")
    .replace(/^_+|_+$/g, "") || "unspecified_issue";
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

function buildClientXlsx(
  moduleKey: string,
  comments: Array<Record<string, unknown>>,
  locale: string,
): Blob {
  const wb = XLSX.utils.book_new();
  const positive = comments.filter((c) => c.sentiment === "positive");
  const negative = comments.filter((c) => c.sentiment === "negative");
  const headers =
    locale === "zh"
      ? ["排名", "标签", "出现次数", "提及占比", "代表性评论（前20条摘要）"]
      : ["Rank", "Tag", "Count", "Percentage", "Representative Reviews (Top 20)"];
  const issueHeaders =
    locale === "zh"
      ? ["排名", "Specific Issue", "出现次数", "提及占比", "Dimension", "Canonical Issue Key", "Aspect Key", "Evidence Span", "Issue Confidence", "代表性评论（前20条摘要）"]
      : ["Rank", "Specific Issue", "Count", "Mention Share", "Dimension", "Canonical Issue Key", "Aspect Key", "Evidence Span", "Issue Confidence", "Representative Reviews (Top 20)"];

  function buildTop10(pool: Array<Record<string, unknown>>, tagField: string) {
    const counter: Record<string, number> = {};
    const sources: Record<string, string[]> = {};
    for (const c of pool) {
      const raw = String(c[tagField] || "");
      if (!raw) continue;
      const seen = new Set<string>();
      for (const t of raw.split(",")) {
        const tag = t.trim();
        if (!tag || seen.has(tag)) continue;
        seen.add(tag);
        counter[tag] = (counter[tag] || 0) + 1;
        if (!sources[tag]) sources[tag] = [];
        if (sources[tag].length < 20) {
          sources[tag].push(String(c.content || "").slice(0, 120));
        }
      }
    }
    const poolSize = pool.length || 1;
    return Object.entries(counter)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([tag, count], i) => [
        i + 1,
        tag,
        count,
        `${((count / poolSize) * 100).toFixed(1)}%`,
        (sources[tag] || []).join(" | "),
      ]);
  }

  function iterSpecificIssueOccurrences(comment: Record<string, unknown>) {
    const payload = parseAspectsPayload(comment);
    const schemaVersion = String(payload?.specific_issue_schema_version || "");
    const content = String(comment.content || "");
    const subCategory = String(payload?.sub_category || comment.sub_category || comment.category || "");
    const occurrences = getAspects(comment)
      .filter((aspect) => {
        return (
          String(aspect.polarity || "").toLowerCase() === "negative" &&
          aspect.display_allowed !== false &&
          Boolean(aspect.specific_issue) &&
          Boolean(aspect.canonical_issue_key)
        );
      })
      .map((aspect) => {
        const aspectKey = String(aspect.key || aspect.aspect_key || "");
        return {
          specificIssue: String(aspect.specific_issue || ""),
          canonicalIssueKey: String(aspect.canonical_issue_key || ""),
          aspectKey,
          dimension: aspectKey
            ? aspectLabel(aspectKey, locale)
            : String(aspect.dimension || aspect.aspect_label || ""),
          evidenceSpan: String(aspect.evidence_span || ""),
          issueConfidence: String(aspect.issue_confidence || ""),
          subCategory,
          content,
        };
      });
    if (occurrences.length > 0 || schemaVersion === "1.0") {
      return occurrences;
    }
    return String(comment.issue_tag || "")
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean)
      .map((tag) => ({
        specificIssue: tag,
        canonicalIssueKey: safeIssueSlug(tag),
        aspectKey: "",
        dimension: "",
        evidenceSpan: "",
        issueConfidence: "low",
        subCategory: String(comment.sub_category || comment.category || ""),
        content,
      }));
  }

  function buildSpecificIssueTop10(pool: Array<Record<string, unknown>>) {
    const groups = new Map<string, {
      specificIssue: string;
      canonicalIssueKey: string;
      aspectKey: string;
      aspectKeys: string[];
      dimension: string;
      dimensions: string[];
      evidenceSpans: string[];
      issueConfidence: string;
      comments: string[];
      count: number;
    }>();

    for (const comment of pool) {
      const counted = new Set<string>();
      const seenOccurrences = new Set<string>();
      for (const occurrence of iterSpecificIssueOccurrences(comment)) {
        const occurrenceKey = `${occurrence.subCategory}::${occurrence.aspectKey}::${occurrence.canonicalIssueKey}`;
        if (!occurrence.canonicalIssueKey || seenOccurrences.has(occurrenceKey)) continue;
        seenOccurrences.add(occurrenceKey);
        const key = `${occurrence.subCategory}::${occurrence.canonicalIssueKey}`;
        const group = groups.get(key) || {
          specificIssue: occurrence.specificIssue,
          canonicalIssueKey: occurrence.canonicalIssueKey,
          aspectKey: occurrence.aspectKey,
          aspectKeys: [],
          dimension: occurrence.dimension,
          dimensions: [],
          evidenceSpans: [],
          issueConfidence: occurrence.issueConfidence || "low",
          comments: [],
          count: 0,
        };
        if (occurrence.aspectKey && !group.aspectKeys.includes(occurrence.aspectKey)) {
          group.aspectKeys.push(occurrence.aspectKey);
        }
        if (occurrence.dimension && !group.dimensions.includes(occurrence.dimension)) {
          group.dimensions.push(occurrence.dimension);
        }
        if (!counted.has(key)) {
          group.count += 1;
          counted.add(key);
        }
        if (occurrence.evidenceSpan && group.evidenceSpans.length < 20) {
          group.evidenceSpans.push(occurrence.evidenceSpan);
        }
        if (occurrence.content && group.comments.length < 20) {
          group.comments.push(occurrence.content.slice(0, 120));
        }
        groups.set(key, group);
      }
    }

    const poolSize = pool.length || 1;
    return Array.from(groups.values())
      .sort((a, b) => b.count - a.count || a.specificIssue.localeCompare(b.specificIssue))
      .slice(0, 10)
      .map((group, i) => [
        i + 1,
        group.specificIssue,
        group.count,
        `${((group.count / poolSize) * 100).toFixed(1)}%`,
        group.dimensions.join(", ") || group.dimension,
        group.canonicalIssueKey,
        group.aspectKeys.join(", ") || group.aspectKey,
        group.evidenceSpans.join(" | "),
        group.issueConfidence,
        group.comments.join(" | "),
      ]);
  }

  if (moduleKey === "user_experience") {
    const posData = [headers, ...buildTop10(positive, "highlight_tag")];
    const wsPos = XLSX.utils.aoa_to_sheet(posData);
    XLSX.utils.book_append_sheet(wb, wsPos, locale === "zh" ? "正向反馈 TOP10" : "Positive Feedback TOP10");
    const negData = [issueHeaders, ...buildSpecificIssueTop10(negative)];
    const wsNeg = XLSX.utils.aoa_to_sheet(negData);
    XLSX.utils.book_append_sheet(wb, wsNeg, locale === "zh" ? "负向反馈 TOP10" : "Negative Feedback TOP10");
  } else if (moduleKey === "purchase_motives") {
    const data = [headers, ...buildTop10(positive, "highlight_tag")];
    const ws = XLSX.utils.aoa_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, locale === "zh" ? "消费动机" : "Purchase Motives");
  } else if (moduleKey === "unmet_needs") {
    const data = [issueHeaders, ...buildSpecificIssueTop10(negative)];
    const ws = XLSX.utils.aoa_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, locale === "zh" ? "未满足的需求" : "Unmet Needs");
  } else if (moduleKey === "consumer_profile") {
    const posData = [headers, ...buildTop10(positive, "highlight_tag")];
    const wsPos = XLSX.utils.aoa_to_sheet(posData);
    XLSX.utils.book_append_sheet(wb, wsPos, locale === "zh" ? "亮点标签 TOP10" : "Highlight Tags TOP10");
    const negData = [headers, ...buildTop10(negative, "issue_tag")];
    const wsNeg = XLSX.utils.aoa_to_sheet(negData);
    XLSX.utils.book_append_sheet(wb, wsNeg, locale === "zh" ? "问题标签 TOP10" : "Issue Tags TOP10");
  } else {
    const ws = XLSX.utils.aoa_to_sheet([headers]);
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
            aspectKey={meta.aspectKey}
            aspectKeys={meta.aspectKeys}
            dimension={meta.dimension}
            subCategory={meta.subCategory}
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
                const tag = String(row.tag || "");
                const origTag = String(origPositive[i]?.tag || tag);
                const pct = Number(row.pct || 0);
                const reason = String(row.reason || "");
                return (
                  <div key={i} className="rounded-card border border-line bg-white p-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-soft">{i + 1}</span>
                      <span className="text-sm font-semibold text-ink">{tag}</span>
                      <span className="text-xs text-soft">{pct.toFixed(1)}%</span>
                    </div>
                    {row.reason ? <p className="mt-1 text-xs text-soft italic">{reason}</p> : null}
                    {renderRowButtons(origTag, pct, reason, "highlight_tag", false)}
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
                const tag = issueLabel(row, issueLabel(origRow || {}, ""));
                const origTag = issueLabel(origRow || {}, tag);
                const meta = issueMetaFromRow(origRow, origTag);
                const dimension = issueDimension(row) || meta.dimension || "";
                const pct = Number(row.pct || 0);
                const reason = String(row.reason || "");
                return (
                  <div key={i} className="rounded-card border border-line bg-white p-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-soft">{i + 1}</span>
                      <span className="text-sm font-semibold text-ink">{tag}</span>
                      <span className="text-xs text-soft">{pct.toFixed(1)}%</span>
                    </div>
                    {row.reason ? <p className="mt-1 text-xs text-soft italic">{reason}</p> : null}
                    {renderRowButtons(origTag, pct, reason, "issue_tag", !!showAction, {
                      ...meta,
                      dimension: meta.dimension || dimension,
                    })}
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
            const pct = Number(row.pct || 0);
            const reason = String(row.reason || row.detail || "");
            const tagSource: "highlight_tag" | "issue_tag" =
              moduleKey === "unmet_needs" ? "issue_tag" : "highlight_tag";
            const canAction = moduleKey === "unmet_needs" && !!showAction;
            const isSpecificIssue = moduleKey === "unmet_needs";
            const tag = isSpecificIssue ? issueLabel(row, issueLabel(origRow || {}, "")) : String(row.tag || row.label || "");
            const origTag = isSpecificIssue
              ? issueLabel(origRow || {}, tag)
              : String(origRow?.tag || origRow?.label || tag);
            const meta = isSpecificIssue ? issueMetaFromRow(origRow, origTag) : {};
            const dimension = isSpecificIssue ? issueDimension(row) || meta.dimension || "" : "";
            return (
              <div key={i} className="rounded-card border border-line bg-[#faf8fb] px-4 py-3">
                <div className="flex items-center gap-2">
                  {tag ? (
                    <span className="text-sm font-semibold text-ink">{tag}</span>
                  ) : null}
                  {row.pct !== undefined && (
                    <span className="text-xs text-soft">{pct.toFixed(1)}%</span>
                  )}
                </div>
                {(row.reason || row.detail) ? (
                  <p className="mt-1 text-xs leading-5 text-soft">{reason}</p>
                ) : null}
                {renderRowButtons(origTag, pct, reason, tagSource, canAction, {
                  ...meta,
                  dimension: meta.dimension || dimension,
                })}
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
