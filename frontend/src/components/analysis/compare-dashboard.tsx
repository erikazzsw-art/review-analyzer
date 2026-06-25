"use client";

import { useState, useCallback } from "react";
import { Download, Languages, Loader2 } from "lucide-react";
import * as XLSX from "xlsx";
import type { AnalysisCompareGroup, AnalysisCompareResponse, AnalysisResultModule } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { translateModule } from "@/lib/api/browser";

type CompareDashboardProps = {
  dataset: AnalysisCompareResponse;
};

function formatRate(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return `${value.toFixed(1)}%`;
}

function formatRating(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return value.toFixed(1);
}

function deltaTone(delta: number, mode: "positive" | "negative"): string {
  if (delta === 0) return "text-soft";
  const isImprovement = mode === "positive" ? delta > 0 : delta < 0;
  return isImprovement ? "text-[#2f9e6b]" : "text-[#b44655]";
}

function deltaLabel(delta: number, suffix: string = "pt"): string {
  if (delta === 0) return `0.0${suffix}`;
  return `${delta > 0 ? "↑" : "↓"}${Math.abs(delta).toFixed(1)}${suffix}`;
}

type TagRow = { tag: string; pct: number; reason?: string };

function normalizeTagRow(row: Record<string, unknown>): TagRow {
  const tag = String(row["tag"] ?? row["label"] ?? row["name"] ?? "-");
  const pctValue =
    typeof row["pct"] === "number"
      ? (row["pct"] as number)
      : Number(row["pct"] ?? row["percentage"] ?? row["percent"] ?? 0);
  const pct = Number.isFinite(pctValue) ? pctValue : 0;
  const reason = row["reason"] ? String(row["reason"]) : undefined;
  return { tag, pct, reason };
}

type DimensionTone = "positive" | "negative" | "neutral";

type DimensionSpec = {
  key: string;
  label: string;
  tone: DimensionTone;
  /** 把某个 group 的 insights 抽出 TOP 标签 list. 若 insights 缺失返回 null */
  rowsFor: (group: AnalysisCompareGroup) => TagRow[] | null;
};

const DIMENSIONS: DimensionSpec[] = [
  {
    key: "consumer_profile",
    label: "用户画像",
    tone: "neutral",
    rowsFor: (group) => {
      const module = group.insights?.consumer_profile;
      if (!module) return null;
      const rows = (module.rows as Array<Record<string, unknown>>) || [];
      // consumer_profile.rows 是 {label, detail} 格式, 不是 {tag, pct}
      // 在没有 tag bar 数据时, 我们走 summary 兜底, 在外层判定
      return rows
        .filter((row) => row["tag"] !== undefined || row["pct"] !== undefined)
        .map(normalizeTagRow);
    },
  },
  {
    key: "user_experience_positive",
    label: "用户体验 · 正向反馈",
    tone: "positive",
    rowsFor: (group) => {
      const module = group.insights?.user_experience;
      if (!module) {
        // fallback: 从 group.top_highlights 兜底
        const fallback = group.top_highlights || [];
        if (!fallback.length) return null;
        return fallback.slice(0, 5).map(normalizeTagRow);
      }
      return (module.positive as Array<Record<string, unknown>> || []).slice(0, 5).map(normalizeTagRow);
    },
  },
  {
    key: "user_experience_negative",
    label: "用户体验 · 负向反馈",
    tone: "negative",
    rowsFor: (group) => {
      const module = group.insights?.user_experience;
      if (!module) {
        const fallback = group.top_issues || [];
        if (!fallback.length) return null;
        return fallback.slice(0, 5).map(normalizeTagRow);
      }
      return (module.negative as Array<Record<string, unknown>> || []).slice(0, 5).map(normalizeTagRow);
    },
  },
  {
    key: "purchase_motives",
    label: "消费动机",
    tone: "neutral",
    rowsFor: (group) => {
      const module = group.insights?.purchase_motives;
      if (!module) return null;
      return ((module.rows as Array<Record<string, unknown>>) || []).slice(0, 5).map(normalizeTagRow);
    },
  },
  {
    key: "unmet_needs",
    label: "未满足的需求",
    tone: "negative",
    rowsFor: (group) => {
      const module = group.insights?.unmet_needs;
      if (!module) return null;
      return ((module.rows as Array<Record<string, unknown>>) || []).slice(0, 5).map(normalizeTagRow);
    },
  },
];

function summaryFor(group: AnalysisCompareGroup, key: keyof NonNullable<AnalysisCompareGroup["insights"]>): string {
  const module = group.insights?.[key] as AnalysisResultModule | undefined;
  return module?.summary || "";
}

export function CompareDashboard({ dataset }: CompareDashboardProps) {
  const groups = dataset.groups;
  if (!groups.length) {
    return (
      <section className="rounded-shell border border-dashed border-line bg-[#fffafb] px-6 py-10 text-sm text-soft">
        当前筛选下没有可用对比数据。请确认产品和评论时间窗口是否合理。
      </section>
    );
  }

  const baseline = groups[0];
  const groupCount = groups.length;
  // grid 列模板: 第 1 列固定 160px 维度名, 后面均分 N 个 group, 末尾 56px 占位列
  const gridTemplate = `160px repeat(${groupCount}, minmax(0, 1fr)) 56px`;

  return (
    <div className="flex flex-col gap-5">
      <section>
        <h3 className="font-heading text-lg font-extrabold tracking-[-0.04em] text-ink">核心指标</h3>
        <p className="mt-1 text-xs text-soft">
          以 <strong className="text-ink">{baseline.label}</strong> 为基准，↑ ↓ 表示相对基准的变化。
        </p>
        <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <KpiColumn title="评论数" mode="raw" baseline={baseline.review_count} groups={groups} field="review_count" />
          <KpiColumn
            title="好评率"
            mode="positive"
            baseline={baseline.positive_rate}
            groups={groups}
            field="positive_rate"
            formatter={formatRate}
          />
          <KpiColumn
            title="差评率"
            mode="negative"
            baseline={baseline.negative_rate}
            groups={groups}
            field="negative_rate"
            formatter={formatRate}
          />
          <KpiColumn
            title="平均评分"
            mode="positive"
            baseline={baseline.avg_rating}
            groups={groups}
            field="avg_rating"
            formatter={formatRating}
          />
        </div>
      </section>

      <DimensionSection dataset={dataset} groups={groups} gridTemplate={gridTemplate} />



      {dataset.empty_groups.length > 0 ? (
        <section className="rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-3 text-sm text-soft">
          以下对象在筛选窗口内没有评论：{dataset.empty_groups.join(" · ")}
        </section>
      ) : null}
    </div>
  );
}

type KpiColumnProps = {
  title: string;
  mode: "positive" | "negative" | "raw";
  baseline: number | null | undefined;
  groups: AnalysisCompareGroup[];
  field: keyof AnalysisCompareGroup;
  formatter?: (value: number | null | undefined) => string;
};

function KpiColumn({ title, mode, baseline, groups, field, formatter }: KpiColumnProps) {
  return (
    <div className="rounded-card border border-line bg-white px-4 py-3">
      <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{title}</div>
      <div className="mt-2 space-y-2">
        {groups.map((group, index) => {
          const rawValue = group[field] as number | null | undefined;
          const baseValue = typeof baseline === "number" ? baseline : 0;
          const currentValue = typeof rawValue === "number" ? rawValue : 0;
          const delta = currentValue - baseValue;
          const displayed = formatter ? formatter(rawValue ?? null) : String(rawValue ?? "-");
          const showDelta = index > 0 && mode !== "raw" && typeof rawValue === "number";
          const showRawDelta = index > 0 && mode === "raw" && typeof rawValue === "number";
          return (
            <div key={`kpi-${title}-${index}`} className="flex items-baseline justify-between gap-2">
              <span className="truncate text-xs text-soft">{group.label}</span>
              <span className="flex items-baseline gap-2">
                <span className="text-base font-semibold text-ink">{displayed}</span>
                {showDelta ? (
                  <span className={`text-xs font-semibold ${deltaTone(delta, mode as "positive" | "negative")}`}>
                    {deltaLabel(delta)}
                  </span>
                ) : null}
                {showRawDelta ? (
                  <span className={`text-xs font-semibold ${delta >= 0 ? "text-[#2f9e6b]" : "text-[#b44655]"}`}>
                    {delta >= 0 ? `+${delta}` : `${delta}`}
                  </span>
                ) : null}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

type DimensionRowProps = {
  dimension: DimensionSpec;
  groups: AnalysisCompareGroup[];
  gridTemplate: string;
};

function DimensionRow({ dimension, groups, gridTemplate }: DimensionRowProps) {
  // 用户画像特殊处理: 如果 insights.consumer_profile.rows 不是 tag/pct 格式, 显示 summary 文本
  const isConsumerProfile = dimension.key === "consumer_profile";
  const groupRows = groups.map((group) => dimension.rowsFor(group));
  const allEmpty = groupRows.every((rows) => rows === null || rows.length === 0);

  if (isConsumerProfile && allEmpty) {
    // 退化为 summary 文本展示
    const summaries = groups.map((group) => summaryFor(group, "consumer_profile"));
    if (summaries.every((text) => !text)) {
      return (
        <div
          className="grid items-start gap-3 px-5 py-4"
          style={{ gridTemplateColumns: gridTemplate }}
        >
          <div className="text-sm font-semibold text-ink">{dimension.label}</div>
          {groups.map((group) => (
            <div key={`empty-${group.label}`} className="text-xs text-soft">--</div>
          ))}
          <div />
        </div>
      );
    }
    return (
      <div
        className="grid items-start gap-3 px-5 py-4"
        style={{ gridTemplateColumns: gridTemplate }}
      >
        <div className="text-sm font-semibold text-ink">{dimension.label}</div>
        {summaries.map((text, idx) => (
          <div key={`summary-${idx}`} className="text-xs leading-5 text-ink">
            {text || "--"}
          </div>
        ))}
        <div />
      </div>
    );
  }

  return (
    <div
      className="grid items-start gap-3 px-5 py-4"
      style={{ gridTemplateColumns: gridTemplate }}
    >
      <div className="text-sm font-semibold text-ink">{dimension.label}</div>
      {groupRows.map((rows, idx) => (
        <DimensionCell key={`cell-${dimension.key}-${idx}`} rows={rows} tone={dimension.tone} />
      ))}
      <div className="text-right text-xs text-soft">--</div>
    </div>
  );
}

function DimensionCell({ rows, tone }: { rows: TagRow[] | null; tone: DimensionTone }) {
  const barColor =
    tone === "positive" ? "bg-[#d6f4e5]" : tone === "negative" ? "bg-[#fbdadd]" : "bg-[#e5edff]";

  if (!rows || rows.length === 0) {
    return <div className="text-xs text-soft">--</div>;
  }

  return (
    <div className="space-y-1.5">
      {rows.map((row, idx) => {
        const width = Math.min(100, Math.max(2, row.pct));
        return (
          <div key={`${row.tag}-${idx}`} className="grid grid-cols-[1fr_72px_44px] items-center gap-2">
            <span className="truncate text-xs text-ink" title={row.tag}>
              {row.tag}
            </span>
            <span className={`h-2 rounded-full ${barColor}`} style={{ width: `${width}%` }} />
            <span className="text-right text-[11px] text-soft">{row.pct.toFixed(1)}%</span>
          </div>
        );
      })}
    </div>
  );
}

type DimensionSectionProps = {
  dataset: AnalysisCompareResponse;
  groups: AnalysisCompareGroup[];
  gridTemplate: string;
};

function DimensionSection({ dataset, groups, gridTemplate }: DimensionSectionProps) {
  const [translating, setTranslating] = useState(false);
  const [translated, setTranslated] = useState(false);
  const [translatedGroups, setTranslatedGroups] = useState<Record<string, Record<string, unknown>> | null>(null);
  const [exporting, setExporting] = useState(false);

  const handleDownload = useCallback(() => {
    setExporting(true);
    try {
      const header = ["维度", ...groups.map((g) => g.label)];
      const rows: string[][] = [header];
      for (const dim of DIMENSIONS) {
        const cells = groups.map((group) => {
          const tagRows = dim.rowsFor(group);
          if (!tagRows || tagRows.length === 0) return "--";
          return tagRows.map((r) => `${r.tag}(${r.pct.toFixed(1)}%)`).join(" / ");
        });
        rows.push([dim.label, ...cells]);
      }
      const ws = XLSX.utils.aoa_to_sheet(rows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "维度对比");
      XLSX.writeFile(wb, `维度对比_${new Date().toISOString().slice(0, 10)}.xlsx`);
    } finally {
      setExporting(false);
    }
  }, [groups]);

  const handleTranslate = useCallback(async () => {
    if (translated) {
      setTranslated(false);
      return;
    }
    if (translatedGroups) {
      setTranslated(true);
      return;
    }
    setTranslating(true);
    try {
      const content: Record<string, unknown> = {};
      for (const dim of DIMENSIONS) {
        content[dim.key] = groups.map((group) => {
          const tagRows = dim.rowsFor(group);
          return tagRows?.map((r) => ({ tag: r.tag, pct: r.pct })) ?? [];
        });
      }
      const result = await translateModule({
        sessionId: 0,
        moduleKey: "compare_dimensions",
        content,
        targetLang: "en",
      });
      setTranslatedGroups(result.translated as Record<string, Record<string, unknown>>);
      setTranslated(true);
    } catch {
      // silently fail
    } finally {
      setTranslating(false);
    }
  }, [translated, translatedGroups, groups]);

  return (
    <section className="rounded-shell border border-line bg-white shadow-card">
      <header className="flex items-center justify-between border-b border-line px-5 py-3">
        <h3 className="font-heading text-base font-extrabold tracking-[-0.04em] text-ink">维度对比</h3>
        <div className="flex items-center gap-1.5">
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
            {translated ? "原文" : "翻译"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
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
      </header>
      <div
        className="grid items-center gap-3 border-b border-line bg-[#fafafa] px-5 py-2 text-[11px] font-semibold uppercase tracking-[0.1em] text-soft"
        style={{ gridTemplateColumns: gridTemplate }}
      >
        <div>维度</div>
        {groups.map((group) => (
          <div key={`head-${group.label}`} className="truncate">
            {group.label}
          </div>
        ))}
        <div />
      </div>
      <div className="divide-y divide-line">
        {DIMENSIONS.map((dimension) => (
          <DimensionRow
            key={dimension.key}
            dimension={dimension}
            groups={groups}
            gridTemplate={gridTemplate}
          />
        ))}
      </div>
    </section>
  );
}

