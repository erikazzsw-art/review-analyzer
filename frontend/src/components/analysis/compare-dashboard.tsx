"use client";

import type { AnalysisCompareGroup, AnalysisCompareResponse } from "@/lib/api/types";

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

function pickPct(row: Record<string, unknown>, label: string): number {
  const raw = row[label];
  if (typeof raw === "number") return raw;
  if (typeof raw !== "string") return 0;
  const numeric = parseFloat(raw.replace("%", ""));
  return Number.isFinite(numeric) ? numeric : 0;
}

type DimensionSpec = {
  key: string;
  label: string;
  tone: "neutral" | "positive" | "negative";
  source: (insights: Record<string, Record<string, unknown>> | null | undefined) => Array<Record<string, unknown>>;
};

const DIMENSIONS: DimensionSpec[] = [
  {
    key: "purchase_motives",
    label: "购买动机",
    tone: "neutral",
    source: (insights) => (insights?.purchase_motives?.rows as Array<Record<string, unknown>>) || [],
  },
  {
    key: "unmet_needs",
    label: "未被满足的需求",
    tone: "neutral",
    source: (insights) => (insights?.unmet_needs?.rows as Array<Record<string, unknown>>) || [],
  },
  {
    key: "experience_positive",
    label: "产品体验 · 正向观点",
    tone: "positive",
    source: (insights) => (insights?.user_experience?.positive as Array<Record<string, unknown>>) || [],
  },
  {
    key: "experience_negative",
    label: "产品体验 · 负向观点",
    tone: "negative",
    source: (insights) => (insights?.user_experience?.negative as Array<Record<string, unknown>>) || [],
  },
];

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
  const hasAnyInsights = groups.some((group) => group.insights && Object.keys(group.insights).length > 0);

  return (
    <div className="flex flex-col gap-5">
      <section>
        <h3 className="font-heading text-lg font-extrabold tracking-[-0.04em] text-ink">核心指标对比</h3>
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

      {hasAnyInsights ? (
        <section className="rounded-shell border border-line bg-white shadow-card">
          <header className="border-b border-line px-5 py-3">
            <h3 className="font-heading text-base font-extrabold tracking-[-0.04em] text-ink">维度对照</h3>
            <p className="mt-1 text-xs text-soft">
              每个维度横向铺开各对比窗口的 TOP 标签和占比。
            </p>
          </header>
          <div className="divide-y divide-line">
            {DIMENSIONS.map((dimension) => (
              <DimensionRow
                key={dimension.key}
                dimension={dimension}
                groups={groups}
              />
            ))}
          </div>
        </section>
      ) : null}

      <DifferenceTable
        title="问题 TOP 变化"
        emptyHint="暂无显著问题差异"
        rows={dataset.issue_differences}
        groups={groups}
        mode="negative"
      />

      <DifferenceTable
        title="亮点 TOP 变化"
        emptyHint="暂无显著亮点差异"
        rows={dataset.highlight_differences}
        groups={groups}
        mode="positive"
      />

      <section className="grid gap-3 xl:grid-cols-2">
        <RiskOpportunityCard
          title="风险对象"
          accent="#fff8f9"
          rows={dataset.risk_groups}
          render={(group) => (
            <>
              差评率 {formatRate(group.negative_rate)} · {group.review_count} 条 · TOP{" "}
              {group.top_issue}
            </>
          )}
          emptyHint="当前没有明显的风险对象。"
        />
        <RiskOpportunityCard
          title="机会对象"
          accent="#f8fffc"
          rows={dataset.opportunity_groups}
          render={(group) => (
            <>
              好评率 {formatRate(group.positive_rate)} · {group.review_count} 条 · TOP{" "}
              {group.top_highlight}
            </>
          )}
          emptyHint="当前没有明显的机会对象。"
        />
      </section>

      {dataset.recommended_actions.length > 0 ? (
        <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
          <h3 className="font-heading text-lg font-extrabold tracking-[-0.04em] text-ink">推荐动作</h3>
          <div className="mt-3 space-y-2">
            {dataset.recommended_actions.map((action, index) => (
              <div key={`action-${index}`} className="rounded-card border border-line bg-white px-4 py-3 text-sm leading-6 text-ink">
                · {action}
              </div>
            ))}
          </div>
        </section>
      ) : null}

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
};

function DimensionRow({ dimension, groups }: DimensionRowProps) {
  const perGroupRows = groups.map((group) => dimension.source(group.insights as Record<string, Record<string, unknown>> | null | undefined).slice(0, 5));
  const hasAnyRow = perGroupRows.some((rows) => rows.length > 0);

  return (
    <div className="grid gap-0 px-5 py-4 md:grid-cols-[160px_1fr]">
      <div className="pr-4 text-sm font-semibold text-ink">
        {dimension.label}
      </div>
      {hasAnyRow ? (
        <div
          className="grid gap-4"
          style={{ gridTemplateColumns: `repeat(${Math.max(groups.length, 1)}, minmax(0, 1fr))` }}
        >
          {groups.map((group, gIdx) => (
            <DimensionGroupColumn
              key={`${dimension.key}-${gIdx}`}
              label={group.label}
              rows={perGroupRows[gIdx]}
              tone={dimension.tone}
            />
          ))}
        </div>
      ) : (
        <div className="text-sm text-soft">--</div>
      )}
    </div>
  );
}

type DimensionGroupColumnProps = {
  label: string;
  rows: Array<Record<string, unknown>>;
  tone: "neutral" | "positive" | "negative";
};

function DimensionGroupColumn({ label, rows, tone }: DimensionGroupColumnProps) {
  const barColor =
    tone === "positive" ? "bg-[#d6f4e5]" : tone === "negative" ? "bg-[#fbdadd]" : "bg-[#e5edff]";

  if (!rows.length) {
    return (
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{label}</div>
        <div className="mt-2 text-xs text-soft">--</div>
      </div>
    );
  }

  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{label}</div>
      <div className="mt-2 space-y-1.5">
        {rows.map((row, idx) => {
          const tag = String(row["tag"] ?? row["label"] ?? "-");
          const pctValue = typeof row["pct"] === "number" ? (row["pct"] as number) : Number(row["pct"] ?? 0);
          const pct = Number.isFinite(pctValue) ? pctValue : 0;
          const width = Math.min(100, Math.max(2, pct));
          return (
            <div key={`${tag}-${idx}`} className="grid grid-cols-[1fr_120px_48px] items-center gap-2">
              <span className="truncate text-xs text-ink" title={tag}>
                {tag}
              </span>
              <span className={`h-2 rounded-full ${barColor}`} style={{ width: `${width}%` }} />
              <span className="text-right text-xs text-soft">{pct.toFixed(1)}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

type DifferenceTableProps = {
  title: string;
  rows: Array<Record<string, unknown>>;
  groups: AnalysisCompareGroup[];
  mode: "positive" | "negative";
  emptyHint: string;
};

function DifferenceTable({ title, rows, groups, mode, emptyHint }: DifferenceTableProps) {
  if (!rows.length) {
    return (
      <section>
        <h3 className="font-heading text-lg font-extrabold tracking-[-0.04em] text-ink">{title}</h3>
        <div className="mt-2 rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-3 text-sm text-soft">
          {emptyHint}
        </div>
      </section>
    );
  }

  const baselineLabel = groups[0]?.label ?? "";

  return (
    <section className="rounded-shell border border-line bg-white shadow-card">
      <header className="flex items-center justify-between border-b border-line px-5 py-3">
        <h3 className="font-heading text-base font-extrabold tracking-[-0.04em] text-ink">{title}</h3>
        <span className="text-xs text-soft">按变化幅度排序 · Top {rows.length}</span>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-[#fafafa] text-xs uppercase tracking-[0.1em] text-soft">
            <tr>
              <th className="px-5 py-2 text-left">标签</th>
              {groups.map((group) => (
                <th key={group.label} className="px-3 py-2 text-right">
                  {group.label}
                </th>
              ))}
              <th className="px-3 py-2 text-right">最高组</th>
              <th className="px-3 py-2 text-right">变化</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const tag = String(row["标签"] ?? row["tag"] ?? "-");
              const basePct = pickPct(row, baselineLabel);
              return (
                <tr key={`diff-${title}-${index}`} className="border-t border-line">
                  <td className="px-5 py-2 text-ink">{tag}</td>
                  {groups.map((group, columnIndex) => {
                    const pct = pickPct(row, group.label);
                    const delta = pct - basePct;
                    const showDelta = columnIndex > 0;
                    return (
                      <td key={`diff-${title}-${index}-${group.label}`} className="px-3 py-2 text-right text-ink">
                        <div className="flex flex-col items-end">
                          <span>{pct.toFixed(1)}%</span>
                          {showDelta ? (
                            <span className={`text-[11px] font-semibold ${deltaTone(delta, mode)}`}>
                              {deltaLabel(delta)}
                            </span>
                          ) : null}
                        </div>
                      </td>
                    );
                  })}
                  <td className="px-3 py-2 text-right text-soft">{String(row["最高组"] ?? "-")}</td>
                  <td className="px-3 py-2 text-right text-soft">{String(row["最大差值"] ?? "-")}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

type RiskOpportunityCardProps = {
  title: string;
  accent: string;
  rows: Array<Record<string, unknown>> | AnalysisCompareGroup[];
  render: (item: AnalysisCompareGroup) => React.ReactNode;
  emptyHint: string;
};

function RiskOpportunityCard({ title, accent, rows, render, emptyHint }: RiskOpportunityCardProps) {
  return (
    <div className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
      <h3 className="font-heading text-lg font-extrabold tracking-[-0.04em] text-ink">{title}</h3>
      <div className="mt-3 space-y-2">
        {rows.length > 0 ? (
          rows.map((row, index) => {
            const group = row as AnalysisCompareGroup;
            return (
              <div
                key={`row-${title}-${index}`}
                className="rounded-card border border-line px-4 py-3 text-sm"
                style={{ background: accent }}
              >
                <div className="font-semibold text-ink">{String(group.label ?? "-")}</div>
                <div className="mt-1 text-soft">{render(group)}</div>
              </div>
            );
          })
        ) : (
          <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-3 text-sm text-soft">
            {emptyHint}
          </div>
        )}
      </div>
    </div>
  );
}
