"use client";

import { useState, type ReactNode } from "react";
import { Download, Languages, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { exportModuleXlsx, translateModule } from "@/lib/api/browser";

type ModuleCardProps = {
  sessionId: number;
  moduleKey: string;
  moduleData: Record<string, unknown>;
  children: ReactNode;
};

export function ModuleCard({ sessionId, moduleKey, moduleData, children }: ModuleCardProps) {
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
      const blob = await exportModuleXlsx(sessionId, moduleKey);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `analysis_${sessionId}_${moduleKey}.xlsx`;
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
      {isTranslated && translatedData ? (
        <TranslatedView data={translatedData} moduleKey={moduleKey} />
      ) : (
        children
      )}
    </section>
  );
}

function TranslatedView({ data, moduleKey }: { data: Record<string, unknown>; moduleKey: string }) {
  const summary = String(data.summary || "");
  const rows = Array.isArray(data.rows) ? data.rows : [];
  const positive = Array.isArray(data.positive) ? data.positive : [];
  const negative = Array.isArray(data.negative) ? data.negative : [];
  const evidence = Array.isArray(data.evidence) ? data.evidence : [];

  return (
    <div className="space-y-4 pt-8">
      {summary && <p className="text-sm leading-7 text-ink">{summary}</p>}

      {moduleKey === "user_experience" && (
        <div className="grid gap-4 xl:grid-cols-2">
          {positive.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-[#059669]">正向反馈</div>
              {positive.map((row: Record<string, unknown>, i: number) => (
                <div key={i} className="rounded-card border border-line bg-white p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-soft">{i + 1}</span>
                    <span className="text-sm font-semibold text-ink">{String(row.tag || "")}</span>
                    <span className="text-xs text-soft">{Number(row.pct || 0).toFixed(1)}%</span>
                  </div>
                  {row.reason ? <p className="mt-1 text-xs text-soft italic">{String(row.reason)}</p> : null}
                </div>
              ))}
            </div>
          )}
          {negative.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-[#dc2626]">负向反馈</div>
              {negative.map((row: Record<string, unknown>, i: number) => (
                <div key={i} className="rounded-card border border-line bg-white p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-soft">{i + 1}</span>
                    <span className="text-sm font-semibold text-ink">{String(row.tag || "")}</span>
                    <span className="text-xs text-soft">{Number(row.pct || 0).toFixed(1)}%</span>
                  </div>
                  {row.reason ? <p className="mt-1 text-xs text-soft italic">{String(row.reason)}</p> : null}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {rows.length > 0 && moduleKey !== "user_experience" && (
        <div className="space-y-2">
          {rows.map((row: Record<string, unknown>, i: number) => (
            <div key={i} className="rounded-card border border-line bg-[#faf8fb] px-4 py-3">
              <div className="flex items-center gap-2">
                {(row.tag || row.label) ? (
                  <span className="text-sm font-semibold text-ink">{String(row.tag || row.label)}</span>
                ) : null}
                {row.pct !== undefined && (
                  <span className="text-xs text-soft">{Number(row.pct || 0).toFixed(1)}%</span>
                )}
              </div>
              {(row.reason || row.detail) ? (
                <p className="mt-1 text-xs leading-5 text-soft">{String(row.reason || row.detail)}</p>
              ) : null}
            </div>
          ))}
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
