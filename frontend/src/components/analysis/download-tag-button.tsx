"use client";

import { FileDown } from "lucide-react";
import { useTranslations } from "next-intl";
import * as XLSX from "xlsx";

type IssueMeta = {
  specificIssue?: string | null;
  canonicalIssueKey?: string | null;
  aspectKey?: string | null;
  dimension?: string | null;
  subCategory?: string | null;
};

type MatchedReview = {
  comment: Record<string, unknown>;
  occurrence: Record<string, unknown> | null;
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

function findSpecificIssueOccurrence(
  comment: Record<string, unknown>,
  meta: IssueMeta,
): Record<string, unknown> | null {
  const aspectKey = String(meta.aspectKey || "").trim();
  const canonicalIssueKey = String(meta.canonicalIssueKey || "").trim();
  const subCategory = String(meta.subCategory || "").trim();
  if (!aspectKey || !canonicalIssueKey) return null;
  const payload = getAspectsPayload(comment);
  if (subCategory && String(payload?.sub_category || comment.sub_category || comment.category || "") !== subCategory) {
    return null;
  }
  return (
    getAspects(comment).find((aspect) => {
      return (
        String(aspect.key || aspect.aspect_key || "") === aspectKey &&
        String(aspect.canonical_issue_key || "") === canonicalIssueKey &&
        String(aspect.polarity || "").toLowerCase() === "negative" &&
        aspect.display_allowed !== false
      );
    }) || null
  );
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
  const hasSpecificIdentity = Boolean(meta.aspectKey && meta.canonicalIssueKey);
  return comments
    .map((comment) => {
      const occurrence = hasSpecificIdentity ? findSpecificIssueOccurrence(comment, meta) : null;
      if (occurrence) return { comment, occurrence };
      if (!hasSpecificIdentity && tagMatchesComment(tag, comment, tagSource)) {
        return { comment, occurrence: null };
      }
      return null;
    })
    .filter((item): item is MatchedReview => Boolean(item));
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
  matched.forEach(({ comment: c, occurrence }, idx) => {
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
      String(occurrence?.specific_issue || meta.specificIssue || ""),
      String(occurrence?.canonical_issue_key || meta.canonicalIssueKey || ""),
      String(meta.dimension || occurrence?.dimension || occurrence?.aspect_label || ""),
      String(occurrence?.key || occurrence?.aspect_key || meta.aspectKey || ""),
      String(occurrence?.evidence_span || ""),
      String(occurrence?.issue_confidence || ""),
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
  const meta = { specificIssue, canonicalIssueKey, aspectKey, dimension, subCategory };
  const count = getMatchedReviews(tag, comments, tagSource, meta).length;

  return (
    <button
      type="button"
      onClick={() => count > 0 && downloadTagReviews(tag, comments, tagSource, locale, translateCategory, meta)}
      disabled={count === 0}
      className="inline-flex items-center gap-1 rounded-md border border-line bg-white px-2 py-1 text-[11px] font-medium text-soft shadow-sm hover:bg-[#faf8fb] hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
      title={count > 0 ? `Download ${count} reviews` : "No matching reviews"}
    >
      <FileDown className="h-3 w-3" />
      {count > 0 ? `Reviews ${count}` : "Reviews 0"}
    </button>
  );
}
