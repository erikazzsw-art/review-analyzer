"use client";

import { FileDown } from "lucide-react";
import { useTranslations } from "next-intl";
import * as XLSX from "xlsx";

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

function downloadTagReviews(
  tag: string,
  comments: Array<Record<string, unknown>>,
  tagSource: "highlight_tag" | "issue_tag",
  locale: string,
  translateCategory: (slug: string) => string,
) {
  const matched = comments.filter((c) => tagMatchesComment(tag, c, tagSource));
  const headers =
    locale === "zh"
      ? ["序号", "评论内容", "评分", "日期", "评论者", "来源", "情感", "分类", "优先级", "分析理由", "改进建议", "问题标签", "亮点标签"]
      : ["No.", "Review", "Rating", "Date", "Reviewer", "Source", "Sentiment", "Category", "Priority", "Reason", "Improvement", "Issue Tags", "Highlight Tags"];
  const data: (string | number)[][] = [headers];
  matched.forEach((c, idx) => {
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
    ] as (string | number)[]);
  });
  const ws = XLSX.utils.aoa_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, tag.slice(0, 31));

  // AI Transparency disclaimer row (California AI Transparency Act AB 2013)
  const aiNote =
    locale === "zh"
      ? "AI 生成分析 · 基于 OpenAI GPT-4o-mini"
      : "Analysis powered by AI (OpenAI GPT-4o-mini)";
  const wsNote = XLSX.utils.aoa_to_sheet([[], [aiNote]]);
  XLSX.utils.book_append_sheet(wb, wsNote, locale === "zh" ? "AI 标注" : "AI Notice");

  XLSX.writeFile(wb, `${tag}_reviews_${matched.length}.xlsx`);
}

export function DownloadTagButton({
  tag,
  comments,
  tagSource,
  locale,
}: {
  tag: string;
  comments: Array<Record<string, unknown>>;
  tagSource: "highlight_tag" | "issue_tag";
  locale: string;
}) {
  const t = useTranslations("categoryLabels");
  const translateCategory = (slug: string): string => {
    try {
      return t(slug);
    } catch {
      return slug;
    }
  };
  const count = comments.filter((c) => tagMatchesComment(tag, c, tagSource)).length;

  return (
    <button
      type="button"
      onClick={() => count > 0 && downloadTagReviews(tag, comments, tagSource, locale, translateCategory)}
      disabled={count === 0}
      className="inline-flex items-center gap-1 rounded-md border border-line bg-white px-2 py-1 text-[11px] font-medium text-soft shadow-sm hover:bg-[#faf8fb] hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
      title={count > 0 ? `Download ${count} reviews` : "No matching reviews"}
    >
      <FileDown className="h-3 w-3" />
      {count > 0 ? `Reviews ${count}` : "Reviews 0"}
    </button>
  );
}
