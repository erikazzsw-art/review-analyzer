"use client";

import { useState, type ReactNode } from "react";
import { Download, Languages, Loader2 } from "lucide-react";
import * as XLSX from "xlsx";

import { Button } from "@/components/ui/button";
import { exportModuleXlsx, translateModule } from "@/lib/api/browser";
import { InlineActionButton } from "@/components/analysis/inline-action-button";
import { DownloadTagButton } from "@/components/analysis/download-tag-button";

type SessionInfo = {
  product_ref_id?: number | null;
  product_id: string;
  version: string;
  custom_title?: string | null;
  auto_title?: string | null;
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
  const [translatedData, setTranslatedData] = useState<Record<string, unknown> | null>(null);
  const [isTranslated, setIsTranslated] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [exporting, setExporting] = useState(false);

  async function handleTranslate() {
    if (isTranslated) {
      setIsTranslated(false);
      return;
    }
    if (translatedData) {
      setIsTranslated(true);
      return;
    }
    setTranslating(true);
    try {
      const result = await translateModule({
        sessionId,
        moduleKey,
        content: moduleData,
        targetLang: "zh",
      });
      setTranslatedData(result.translated);
      setIsTranslated(true);
    } catch {
      // silently fail
    } finally {
      setTranslating(false);
    }
  }

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
        <Button
          variant="outline"
          size="sm"
          onClick={handleTranslate}
          disabled={translating}
          className="h-7 gap-1 px-2.5 text-[11px]"
        >
          {translating ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Languages className="h-3 w-3" />
          )}
          {isTranslated ? "原文" : "翻译"}
        </Button>
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
        {isTranslated && translatedData ? (
          <TranslatedView
            data={translatedData}
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
    </section>
  );
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

  if (moduleKey === "user_experience") {
    const posData = [headers, ...buildTop10(positive, "highlight_tag")];
    const wsPos = XLSX.utils.aoa_to_sheet(posData);
    XLSX.utils.book_append_sheet(wb, wsPos, locale === "zh" ? "正向反馈 TOP10" : "Positive Feedback TOP10");
    const negData = [headers, ...buildTop10(negative, "issue_tag")];
    const wsNeg = XLSX.utils.aoa_to_sheet(negData);
    XLSX.utils.book_append_sheet(wb, wsNeg, locale === "zh" ? "负向反馈 TOP10" : "Negative Feedback TOP10");
  } else if (moduleKey === "purchase_motives") {
    const data = [headers, ...buildTop10(positive, "highlight_tag")];
    const ws = XLSX.utils.aoa_to_sheet(data);
    XLSX.utils.book_append_sheet(wb, ws, locale === "zh" ? "消费动机" : "Purchase Motives");
  } else if (moduleKey === "unmet_needs") {
    const data = [headers, ...buildTop10(negative, "issue_tag")];
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
  const summary = String(data.summary || "");
  const rows = Array.isArray(data.rows) ? data.rows : [];
  const positive = Array.isArray(data.positive) ? data.positive : [];
  const negative = Array.isArray(data.negative) ? data.negative : [];
  const evidence = Array.isArray(data.evidence) ? data.evidence : [];

  const origPositive = Array.isArray(originalData.positive) ? originalData.positive as Record<string, unknown>[] : [];
  const origNegative = Array.isArray(originalData.negative) ? originalData.negative as Record<string, unknown>[] : [];
  const origRows = Array.isArray(originalData.rows) ? originalData.rows as Record<string, unknown>[] : [];

  function renderRowButtons(tag: string, pct: number, reason: string, tagSource: "highlight_tag" | "issue_tag", canAction: boolean) {
    return (
      <div className="mt-2 flex items-center gap-1.5">
        {comments && (
          <DownloadTagButton
            tag={tag}
            comments={comments}
            tagSource={tagSource}
            locale={locale || "zh"}
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
              <div className="text-xs font-semibold text-[#059669]">正向反馈</div>
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
              <div className="text-xs font-semibold text-[#dc2626]">负向反馈</div>
              {negative.map((row: Record<string, unknown>, i: number) => {
                const tag = String(row.tag || "");
                const origTag = String(origNegative[i]?.tag || tag);
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
                    {renderRowButtons(origTag, pct, reason, "issue_tag", !!showAction)}
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
            const tag = String(row.tag || row.label || "");
            const origTag = String(origRows[i]?.tag || origRows[i]?.label || tag);
            const pct = Number(row.pct || 0);
            const reason = String(row.reason || row.detail || "");
            const tagSource: "highlight_tag" | "issue_tag" =
              moduleKey === "unmet_needs" ? "issue_tag" : "highlight_tag";
            const canAction = moduleKey === "unmet_needs" && !!showAction;
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
                {renderRowButtons(origTag, pct, reason, tagSource, canAction)}
              </div>
            );
          })}
        </div>
      )}

      {evidence.length > 0 && (
        <div className="rounded-card border border-dashed border-line bg-[#fdfcfe] p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.08em] text-soft">证据</div>
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
