"use client";

import { FileDown } from "lucide-react";
import { useTranslations } from "next-intl";
import * as XLSX from "xlsx";

import { aspectLabel } from "@/lib/aspect-labels";

type IssueMeta = {
  specificIssue?: string | null;
  canonicalIssueKey?: string | null;
  aspectKey?: string | null;
  aspectKeys?: string[] | null;
  dimension?: string | null;
  subCategory?: string | null;
};

type MatchedReview = {
  comment: Record<string, unknown>;
  occurrences: Array<Record<string, unknown>>;
};

function getAspectsPayload(comment: Record<string, unknown>): Record<string, unknown> | null {
  const raw = comment.aspects_json;
  let parsed: unknown = raw;
  if (typeof raw === "string" && raw.trim()) {
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = null;
    }
  }
  return parsed && typeof parsed === "object" && !Array.isArray(parsed)
    ? (parsed as Record<string, unknown>)
    : null;
}

function getAspects(comment: Record<string, unknown>): Array<Record<string, unknown>> {
  const aspects = getAspectsPayload(comment)?.aspects;
  return Array.isArray(aspects)
    ? aspects.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
    : [];
}

function splitMetaValues(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item || "").trim()).filter(Boolean);
  }
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function uniqueValues(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

function metaAspectKeys(meta: IssueMeta): string[] {
  return uniqueValues([...splitMetaValues(meta.aspectKeys), ...splitMetaValues(meta.aspectKey)]);
}

function findSpecificIssueOccurrences(
  comment: Record<string, unknown>,
  meta: IssueMeta,
): Array<Record<string, unknown>> {
  const aspectKeys = metaAspectKeys(meta);
  const canonicalIssueKey = String(meta.canonicalIssueKey || "").trim();
  const subCategory = String(meta.subCategory || "").trim();
  if (aspectKeys.length === 0 || !canonicalIssueKey) return [];
  const payload = getAspectsPayload(comment);
  if (subCategory && String(payload?.sub_category || comment.sub_category || comment.category || "") !== subCategory) {
    return [];
  }
  return getAspects(comment).filter((aspect) => {
    return (
      aspectKeys.includes(String(aspect.key || aspect.aspect_key || "")) &&
      String(aspect.canonical_issue_key || "") === canonicalIssueKey &&
      String(aspect.polarity || "").toLowerCase() === "negative" &&
      aspect.display_allowed !== false
    );
  });
}

function tagMatchesComment(
  searchTag: string,
  comment: Record<string, unknown>,
  tagSource: "highlight_tag" | "issue_tag",
): boolean {
  const needle = searchTag.trim().toLowerCase();
  if (!needle) return false;

  const raw = String(comment[tagSource] || "");
  if (!raw) return false;
  const commentTags = raw.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);

  return commentTags.includes(needle);
}

function getMatchedReviews(
  tag: string,
  comments: Array<Record<string, unknown>>,
  tagSource: "highlight_tag" | "issue_tag",
  meta: IssueMeta,
): MatchedReview[] {
  const hasSpecificIdentity = Boolean(metaAspectKeys(meta).length > 0 && meta.canonicalIssueKey);
  return comments
    .map((comment) => {
      const occurrences = hasSpecificIdentity ? findSpecificIssueOccurrences(comment, meta) : [];
      if (occurrences.length > 0) return { comment, occurrences };
      if (!hasSpecificIdentity && tagMatchesComment(tag, comment, tagSource)) {
        return { comment, occurrences: [] };
      }
      return null;
    })
    .filter((item): item is MatchedReview => Boolean(item));
}

function joinOccurrenceValues(
  occurrences: Array<Record<string, unknown>>,
  pick: (occurrence: Record<string, unknown>) => unknown,
  fallback = "",
): string {
  const values = uniqueValues(
    occurrences
      .map((occurrence) => String(pick(occurrence) || "").trim())
      .filter(Boolean),
  );
  return values.length > 0 ? values.join(", ") : fallback;
}

function occurrenceAspectKey(occurrence: Record<string, unknown>): string {
  return String(occurrence.key || occurrence.aspect_key || "").trim();
}

function occurrenceDimension(occurrence: Record<string, unknown>, locale: string): string {
  const aspectKey = occurrenceAspectKey(occurrence);
  return aspectKey
    ? aspectLabel(aspectKey, locale)
    : String(occurrence.dimension || occurrence.aspect_label || "").trim();
}

function safeSheetName(value: string): string {
  return (value || "Reviews").replace(/[\\/?*[\]:]+/g, "_").slice(0, 31) || "Reviews";
}

function safeFilenamePart(value: string): string {
  return value.trim().replace(/[\\/:*?"<>|]+/g, "_").replace(/\s+/g, "_") || "reviews";
}

function downloadTagReviews(
  tag: string,
  comments: Array<Record<string, unknown>>,
  tagSource: "highlight_tag" | "issue_tag",
  locale: string,
  translateCategory: (slug: string) => string,
  meta: IssueMeta,
) {
  const matched = getMatchedReviews(tag, comments, tagSource, meta);
  const headers =
    locale === "zh"
      ? ["序号", "评论内容", "评分", "日期", "评论者", "来源", "情感", "分类", "优先级", "分析理由", "改进建议", "问题标签", "亮点标签", "Specific Issue", "Canonical Issue Key", "Dimension", "Aspect Key", "Evidence Span", "Issue Confidence"]
      : ["No.", "Review", "Rating", "Date", "Reviewer", "Source", "Sentiment", "Category", "Priority", "Reason", "Improvement", "Issue Tags", "Highlight Tags", "Specific Issue", "Canonical Issue Key", "Dimension", "Aspect Key", "Evidence Span", "Issue Confidence"];
  const data: (string | number)[][] = [headers];
  matched.forEach(({ comment: c, occurrences }, idx) => {
    const categorySlug = String(c.category || "");
    data.push([
      idx + 1,
      String(c.content || ""),
      c.rating != null ? Number(c.rating) : "",
      String(c.date || ""),
      String(c.reviewer || ""),
      String(c.source || ""),
      String(c.sentiment || ""),
      categorySlug ? translateCategory(categorySlug) : "",
      String(c.priority || ""),
      String(c.reason || ""),
      String(c.improvement || ""),
      String(c.issue_tag || ""),
      String(c.highlight_tag || ""),
      joinOccurrenceValues(occurrences, (occurrence) => occurrence.specific_issue, String(meta.specificIssue || "")),
      joinOccurrenceValues(
        occurrences,
        (occurrence) => occurrence.canonical_issue_key,
        String(meta.canonicalIssueKey || ""),
      ),
      joinOccurrenceValues(
        occurrences,
        (occurrence) => occurrenceDimension(occurrence, locale),
        String(meta.dimension || ""),
      ),
      joinOccurrenceValues(
        occurrences,
        occurrenceAspectKey,
        metaAspectKeys(meta).join(", "),
      ),
      joinOccurrenceValues(occurrences, (occurrence) => occurrence.evidence_span),
      joinOccurrenceValues(occurrences, (occurrence) => occurrence.issue_confidence),
    ] as (string | number)[]);
  });
  const ws = XLSX.utils.aoa_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, safeSheetName(tag));

  // AI Transparency disclaimer row (California AI Transparency Act AB 2013)
  const aiNote =
    locale === "zh"
      ? "AI 生成分析 · 基于 OpenAI GPT-4o-mini"
      : "Analysis powered by AI (OpenAI GPT-4o-mini)";
  const wsNote = XLSX.utils.aoa_to_sheet([[], [aiNote]]);
  XLSX.utils.book_append_sheet(wb, wsNote, locale === "zh" ? "AI 标注" : "AI Notice");

  XLSX.writeFile(wb, `${safeFilenamePart(tag)}_reviews_${matched.length}.xlsx`);
}

export function DownloadTagButton({
  tag,
  comments,
  tagSource,
  locale,
  specificIssue,
  canonicalIssueKey,
  aspectKey,
  aspectKeys,
  dimension,
  subCategory,
}: {
  tag: string;
  comments: Array<Record<string, unknown>>;
  tagSource: "highlight_tag" | "issue_tag";
  locale: string;
  specificIssue?: string | null;
  canonicalIssueKey?: string | null;
  aspectKey?: string | null;
  aspectKeys?: string[] | null;
  dimension?: string | null;
  subCategory?: string | null;
}) {
  const t = useTranslations("categoryLabels");
  const translateCategory = (slug: string): string => {
    try {
      return t(slug);
    } catch {
      return slug;
    }
  };
  const meta = { specificIssue, canonicalIssueKey, aspectKey, aspectKeys, dimension, subCategory };
  const count = getMatchedReviews(tag, comments, tagSource, meta).length;
  if (count === 0) {
    return null;
  }

  return (
    <button
      type="button"
      onClick={() => downloadTagReviews(tag, comments, tagSource, locale, translateCategory, meta)}
      className="inline-flex items-center gap-1 rounded-md border border-line bg-white px-2 py-1 text-[11px] font-medium text-soft shadow-sm hover:bg-[#faf8fb] hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
      title={`Download ${count} reviews`}
    >
      <FileDown className="h-3 w-3" />
      {`Reviews ${count}`}
    </button>
  );
}
