"use client";

import { FileDown } from "lucide-react";
import * as XLSX from "xlsx";

import {
  customerLabelOccurrences,
  type CustomerLabelOccurrence,
} from "@/lib/customer-labels";

type IssueMeta = {
  specificIssue?: string | null;
  canonicalIssueKey?: string | null;
  customerHighlight?: string | null;
  canonicalHighlightKey?: string | null;
  aspectKey?: string | null;
  aspectKeys?: string[] | null;
  dimension?: string | null;
  subCategory?: string | null;
  mentionShare?: number | null;
  impactReviewShare?: number | null;
};

type MatchedOccurrence = {
  comment: Record<string, unknown>;
  occurrence: CustomerLabelOccurrence;
};

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

function labelTypeFromSource(tagSource: "highlight_tag" | "issue_tag"): "issue" | "highlight" {
  return tagSource === "issue_tag" ? "issue" : "highlight";
}

function metaCanonicalKey(meta: IssueMeta, labelType: "issue" | "highlight"): string {
  return String(labelType === "issue" ? meta.canonicalIssueKey || "" : meta.canonicalHighlightKey || "").trim();
}

function metaLabel(meta: IssueMeta, tag: string, labelType: "issue" | "highlight"): string {
  return String(labelType === "issue" ? meta.specificIssue || tag : meta.customerHighlight || tag).trim();
}

function occurrenceMatches(
  occurrence: CustomerLabelOccurrence,
  meta: IssueMeta,
  tag: string,
  labelType: "issue" | "highlight",
): boolean {
  if (occurrence.type !== labelType) return false;
  const canonicalKey = metaCanonicalKey(meta, labelType);
  const expectedLabel = metaLabel(meta, tag, labelType).toLowerCase();
  const subCategory = String(meta.subCategory || "").trim();
  const aspectKeys = metaAspectKeys(meta);
  if (subCategory && occurrence.subCategory && occurrence.subCategory !== subCategory) {
    return false;
  }
  if (canonicalKey) {
    if (occurrence.canonicalLabelKey !== canonicalKey) return false;
  } else if (expectedLabel && occurrence.label.toLowerCase() !== expectedLabel) {
    return false;
  }
  if (aspectKeys.length > 0 && occurrence.aspectKey && !aspectKeys.includes(occurrence.aspectKey)) {
    return false;
  }
  return true;
}

function getMatchedOccurrences(
  tag: string,
  comments: Array<Record<string, unknown>>,
  tagSource: "highlight_tag" | "issue_tag",
  meta: IssueMeta,
  locale: string,
): MatchedOccurrence[] {
  const labelType = labelTypeFromSource(tagSource);
  const matched: MatchedOccurrence[] = [];
  for (const comment of comments) {
    for (const occurrence of customerLabelOccurrences(comment, labelType, locale)) {
      if (occurrenceMatches(occurrence, meta, tag, labelType)) {
        matched.push({ comment, occurrence });
      }
    }
  }
  return matched;
}

function uniqueReviewCount(matches: MatchedOccurrence[]): number {
  const ids = new Set<string>();
  matches.forEach(({ comment }, index) => {
    ids.add(String(comment.id ?? `${comment.content || ""}-${index}`));
  });
  return ids.size;
}

function safeSheetName(value: string): string {
  return (value || "Reviews").replace(/[\\/?*[\]:]+/g, "_").slice(0, 31) || "Reviews";
}

function safeFilenamePart(value: string): string {
  return value.trim().replace(/[\\/:*?"<>|]+/g, "_").replace(/\s+/g, "_") || "reviews";
}

function formatShare(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)}%` : "";
}

function occurrenceRows(
  matches: MatchedOccurrence[],
  meta: IssueMeta,
  tag: string,
): (string | number)[][] {
  return matches.map(({ comment, occurrence }) => {
    const recordScope = occurrence.evidenceVerified && occurrence.evidenceSpan
      ? "Verified Evidence"
      : "Related Review";
    return [
      occurrence.type === "issue" ? "Issue" : "Highlight",
      metaLabel(meta, tag, occurrence.type),
      occurrence.canonicalLabelKey || metaCanonicalKey(meta, occurrence.type),
      formatShare(meta.mentionShare),
      formatShare(meta.impactReviewShare),
      occurrence.rawLabel,
      occurrence.dimension || meta.dimension || "",
      occurrence.evidenceSpan,
      occurrence.evidenceVerified ? "true" : "false",
      occurrence.clusterPropagated ? "true" : "false",
      String(comment.content || ""),
      comment.rating != null ? Number(comment.rating) : "",
      String(comment.date || ""),
      String(comment.reviewer || ""),
      occurrence.confidence,
      occurrence.source || (occurrence.legacyFallback ? "legacy" : ""),
      recordScope,
    ];
  });
}

function downloadOccurrencesXlsx(
  tag: string,
  matches: MatchedOccurrence[],
  meta: IssueMeta,
  locale: string,
) {
  const headers =
    locale === "zh"
      ? ["Type", "Customer Issue / Label", "Canonical Label Key", "Mention Share", "Impact Review Share", "Raw Label", "Aspect", "Evidence Span", "Evidence Verified", "Cluster Propagated", "Review", "Rating", "Date", "Reviewer", "Confidence", "Source", "Record Scope"]
      : ["Type", "Customer Issue / Label", "Canonical Label Key", "Mention Share", "Impact Review Share", "Raw Label", "Aspect", "Evidence Span", "Evidence Verified", "Cluster Propagated", "Review", "Rating", "Date", "Reviewer", "Confidence", "Source", "Record Scope"];
  const ws = XLSX.utils.aoa_to_sheet([headers, ...occurrenceRows(matches, meta, tag)]);
  ws["!cols"] = [
    { wch: 12 },
    { wch: 28 },
    { wch: 28 },
    { wch: 16 },
    { wch: 20 },
    { wch: 24 },
    { wch: 22 },
    { wch: 36 },
    { wch: 18 },
    { wch: 18 },
    { wch: 64 },
    { wch: 8 },
    { wch: 14 },
    { wch: 18 },
    { wch: 14 },
    { wch: 18 },
    { wch: 18 },
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, safeSheetName("Evidence + Related Reviews"));
  const aiNote =
    locale === "zh"
      ? "AI 生成分析 · 基于 OpenAI GPT-4o-mini"
      : "Analysis powered by AI (OpenAI GPT-4o-mini)";
  const wsNote = XLSX.utils.aoa_to_sheet([[], [aiNote]]);
  XLSX.utils.book_append_sheet(wb, wsNote, locale === "zh" ? "AI 标注" : "AI Notice");

  const reviewCount = uniqueReviewCount(matches);
  XLSX.writeFile(
    wb,
    `${safeFilenamePart(tag)}_evidence_and_related_reviews_${matches.length}occurrences_${reviewCount}reviews.xlsx`,
  );
}

export function DownloadTagButton({
  tag,
  comments,
  tagSource,
  locale,
  specificIssue,
  canonicalIssueKey,
  customerHighlight,
  canonicalHighlightKey,
  aspectKey,
  aspectKeys,
  dimension,
  subCategory,
  mentionShare,
  impactReviewShare,
}: {
  tag: string;
  comments: Array<Record<string, unknown>>;
  tagSource: "highlight_tag" | "issue_tag";
  locale: string;
  specificIssue?: string | null;
  canonicalIssueKey?: string | null;
  customerHighlight?: string | null;
  canonicalHighlightKey?: string | null;
  aspectKey?: string | null;
  aspectKeys?: string[] | null;
  dimension?: string | null;
  subCategory?: string | null;
  mentionShare?: number | null;
  impactReviewShare?: number | null;
}) {
  const meta = {
    specificIssue,
    canonicalIssueKey,
    customerHighlight,
    canonicalHighlightKey,
    aspectKey,
    aspectKeys,
    dimension,
    subCategory,
    mentionShare,
    impactReviewShare,
  };
  const matches = getMatchedOccurrences(tag, comments, tagSource, meta, locale);
  if (matches.length === 0) {
    return null;
  }

  const evidenceCount = matches.filter(
    ({ occurrence }) => occurrence.evidenceVerified && Boolean(occurrence.evidenceSpan),
  ).length;
  const relatedReviewCount = uniqueReviewCount(matches);

  return (
    <button
      type="button"
      onClick={() => downloadOccurrencesXlsx(tag, matches, meta, locale)}
      className="inline-flex items-center gap-1 rounded-md border border-line bg-white px-2 py-1 text-[11px] font-medium text-soft shadow-sm hover:bg-[#faf8fb] hover:text-ink"
      title={`Download ${matches.length} label occurrences across ${relatedReviewCount} reviews; ${evidenceCount} verified evidence occurrences`}
    >
      <FileDown className="h-3 w-3" />
      {locale.startsWith("zh")
        ? `Download Evidence + Reviews ${relatedReviewCount}`
        : `Download Evidence + Reviews ${relatedReviewCount}`}
    </button>
  );
}
