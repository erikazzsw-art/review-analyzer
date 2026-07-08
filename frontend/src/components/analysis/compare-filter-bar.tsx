"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import type { CompareFilterGroup, ProductOverview } from "@/lib/api/types";

type CompareMode = "same_product_time" | "same_product_version" | "multi_product";

type CompareFilterBarProps = {
  products: ProductOverview[];
  initialMode?: CompareMode;
  initialGroups?: CompareFilterGroup[];
  isSubmitting?: boolean;
  onSubmit: (mode: CompareMode, groups: CompareFilterGroup[]) => void;
};

const MODE_KEYS: Record<CompareMode, string> = {
  same_product_time: "modeTime",
  same_product_version: "modeVersion",
  multi_product: "modeMulti",
};

const TIME_PRESET_DAYS: Array<{ value: string; key: string; days: number }> = [
  { value: "7", key: "timePreset7", days: 7 },
  { value: "14", key: "timePreset14", days: 14 },
  { value: "30", key: "timePreset30", days: 30 },
  { value: "60", key: "timePreset60", days: 60 },
  { value: "custom", key: "timePresetCustom", days: -1 },
];

const PRESET_WINDOW_DAYS: Array<{ value: string; key: string; days: number }> = [
  { value: "7d", key: "windowPreset7d", days: 7 },
  { value: "14d", key: "windowPreset14d", days: 14 },
  { value: "30d", key: "windowPreset30d", days: 30 },
  { value: "60d", key: "windowPreset60d", days: 60 },
  { value: "180d", key: "windowPreset180d", days: 180 },
  { value: "all", key: "windowPresetAll", days: 0 },
  { value: "custom", key: "windowPresetCustom", days: -1 },
];

function isoDaysAgo(days: number, anchor?: string | null): string {
  const base = anchor ? new Date(`${anchor}T00:00:00Z`) : new Date();
  base.setUTCDate(base.getUTCDate() - days);
  return base.toISOString().slice(0, 10);
}

function todayIso(anchor?: string | null): string {
  if (anchor) return anchor;
  return new Date().toISOString().slice(0, 10);
}

type RowState = {
  productId: string;
  version: string;
  windowPreset: string;
  dateStart: string;
  dateEnd: string;
  label: string;
};

function emptyRow(): RowState {
  return {
    productId: "",
    version: "",
    windowPreset: "30d",
    dateStart: isoDaysAgo(30),
    dateEnd: todayIso(),
    label: "",
  };
}

function rowsForMode(mode: CompareMode, productId: string, baselineLabel: string, compareLabel: string): RowState[] {
  if (mode === "same_product_version") {
    return [
      { ...emptyRow(), productId, label: baselineLabel },
      { ...emptyRow(), productId, label: compareLabel },
    ];
  }
  // multi_product
  return [emptyRow(), emptyRow()];
}

function rowToFilterGroup(row: RowState): CompareFilterGroup | null {
  if (!row.productId) return null;
  const versions = row.version ? [row.version] : [];
  const group: CompareFilterGroup = {
    productId: row.productId,
    versions,
  };
  if (row.windowPreset !== "all") {
    group.dateStart = row.dateStart || undefined;
    group.dateEnd = row.dateEnd || undefined;
  }
  if (row.label.trim()) {
    group.label = row.label.trim();
  }
  return group;
}

// 时间环比模式: 选一次产品 + 版本 + 环比口径, 自动算两段窗口。
type TimeRowState = {
  productId: string;
  version: string;
  presetValue: string;
  baselineStart: string;
  baselineEnd: string;
  compareStart: string;
  compareEnd: string;
};

function timeRowsFromPreset(
  presetValue: string,
  anchor?: string | null,
): {
  baselineStart: string;
  baselineEnd: string;
  compareStart: string;
  compareEnd: string;
} {
  const preset = TIME_PRESET_DAYS.find((item) => item.value === presetValue);
  if (!preset || preset.value === "custom" || preset.days < 0) {
    // 自定义默认仍以 30 天回退展示
    return {
      baselineStart: isoDaysAgo(60, anchor),
      baselineEnd: isoDaysAgo(31, anchor),
      compareStart: isoDaysAgo(30, anchor),
      compareEnd: todayIso(anchor),
    };
  }
  const days = preset.days;
  return {
    baselineStart: isoDaysAgo(days * 2, anchor),
    baselineEnd: isoDaysAgo(days + 1, anchor),
    compareStart: isoDaysAgo(days, anchor),
    compareEnd: todayIso(anchor),
  };
}

function emptyTimeRow(productId: string, anchor?: string | null): TimeRowState {
  return {
    productId,
    version: "",
    presetValue: "30",
    ...timeRowsFromPreset("30", anchor),
  };
}

function timeRowToFilterGroups(row: TimeRowState, baselineLabel: string, compareLabel: string): CompareFilterGroup[] {
  if (!row.productId) return [];
  const versions = row.version ? [row.version] : [];
  return [
    {
      productId: row.productId,
      versions,
      dateStart: row.baselineStart || undefined,
      dateEnd: row.baselineEnd || undefined,
      label: baselineLabel,
    },
    {
      productId: row.productId,
      versions,
      dateStart: row.compareStart || undefined,
      dateEnd: row.compareEnd || undefined,
      label: compareLabel,
    },
  ];
}

export function CompareFilterBar({
  products,
  initialMode = "same_product_time",
  initialGroups,
  isSubmitting,
  onSubmit,
}: CompareFilterBarProps) {
  const t = useTranslations("analysis.compare");
  const tCommon = useTranslations("common");
  const [mode, setMode] = useState<CompareMode>(initialMode);
  const firstProductId = products[0]?.parent_product_id ?? "";
  const productAnchorMap = useMemo(() => {
    const map = new Map<string, string | null>();
    products.forEach((product) => {
      map.set(product.parent_product_id, product.latest_review_date ?? null);
    });
    return map;
  }, [products]);
  const productRangeMap = useMemo(() => {
    const map = new Map<string, { earliest: string | null; latest: string | null }>();
    products.forEach((product) => {
      map.set(product.parent_product_id, {
        earliest: product.earliest_review_date ?? null,
        latest: product.latest_review_date ?? null,
      });
    });
    return map;
  }, [products]);

  const versionAnchorMap = useMemo(() => {
    const map = new Map<string, string | null>();
    products.forEach((product) => {
      const ranges = product.version_date_ranges ?? {};
      Object.entries(ranges).forEach(([version, range]) => {
        map.set(`${product.parent_product_id}::${version}`, range.latest ?? null);
      });
    });
    return map;
  }, [products]);

  const versionRangeMap = useMemo(() => {
    const map = new Map<string, { earliest: string | null; latest: string | null }>();
    products.forEach((product) => {
      const ranges = product.version_date_ranges ?? {};
      Object.entries(ranges).forEach(([version, range]) => {
        map.set(`${product.parent_product_id}::${version}`, range);
      });
    });
    return map;
  }, [products]);

  function anchorFor(productId: string, version?: string): string | null {
    if (version) {
      const versionAnchor = versionAnchorMap.get(`${productId}::${version}`);
      if (versionAnchor) return versionAnchor;
    }
    return productAnchorMap.get(productId) ?? null;
  }

  function rangeLabelFor(productId: string, version?: string): string | null {
    if (version) {
      const vRange = versionRangeMap.get(`${productId}::${version}`);
      if (vRange && (vRange.earliest || vRange.latest)) {
        return t("dateRangeLabel", { start: vRange.earliest || "…", end: vRange.latest || "…" });
      }
    }
    const range = productRangeMap.get(productId);
    if (!range || (!range.earliest && !range.latest)) return null;
    return t("dateRangeLabel", { start: range.earliest || "…", end: range.latest || "…" });
  }

  const [rows, setRows] = useState<RowState[]>(() => {
    if (
      initialMode !== "same_product_time" &&
      initialGroups &&
      initialGroups.length > 0
    ) {
      return initialGroups.map((group) => ({
        productId: group.productId,
        version: group.versions[0] ?? "",
        windowPreset: "custom",
        dateStart: group.dateStart ?? isoDaysAgo(30, productAnchorMap.get(group.productId)),
        dateEnd: group.dateEnd ?? todayIso(productAnchorMap.get(group.productId)),
        label: group.label ?? "",
      }));
    }
    return rowsForMode(
      initialMode === "same_product_time" ? "multi_product" : initialMode,
      firstProductId,
      t("baselineVersion"),
      t("compareVersion"),
    );
  });
  const [timeRow, setTimeRow] = useState<TimeRowState>(() => {
    if (initialMode === "same_product_time" && initialGroups && initialGroups.length >= 2) {
      const [baseline, current] = initialGroups;
      const anchor = productAnchorMap.get(baseline.productId);
      return {
        productId: baseline.productId,
        version: baseline.versions[0] ?? "",
        presetValue: "custom",
        baselineStart: baseline.dateStart ?? isoDaysAgo(60, anchor),
        baselineEnd: baseline.dateEnd ?? isoDaysAgo(31, anchor),
        compareStart: current.dateStart ?? isoDaysAgo(30, anchor),
        compareEnd: current.dateEnd ?? todayIso(anchor),
      };
    }
    return emptyTimeRow(firstProductId, productAnchorMap.get(firstProductId));
  });
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (mode === "same_product_time") {
      if (!timeRow.productId && firstProductId) {
        setTimeRow((prev) => ({ ...prev, productId: firstProductId }));
      }
      return;
    }
    if (!rows.some((row) => row.productId) && firstProductId) {
      setRows((prev) =>
        prev.map((row) => (row.productId ? row : { ...row, productId: firstProductId })),
      );
    }
  }, [firstProductId, rows, mode, timeRow.productId]);

  const productOptions = useMemo(
    () =>
      products.map((product) => ({
        value: product.parent_product_id,
        label: product.name
          ? `${product.parent_product_id} · ${product.name}`
          : product.parent_product_id,
        versions: product.session_versions ?? [],
      })),
    [products],
  );

  const productVersionsMap = useMemo(() => {
    const map = new Map<string, string[]>();
    productOptions.forEach((option) => map.set(option.value, option.versions));
    return map;
  }, [productOptions]);

  function applyMode(nextMode: CompareMode): void {
    setMode(nextMode);
    setError("");
    if (nextMode === "same_product_time") {
      setTimeRow(emptyTimeRow(firstProductId, anchorFor(firstProductId)));
    } else {
      setRows(rowsForMode(nextMode, firstProductId, t("baselineVersion"), t("compareVersion")));
    }
  }

  function updateRow(index: number, patch: Partial<RowState>): void {
    setRows((prev) => prev.map((row, idx) => (idx === index ? { ...row, ...patch } : row)));
  }

  function applyPreset(index: number, preset: string): void {
    const target = PRESET_WINDOW_DAYS.find((item) => item.value === preset);
    if (!target) return;
    if (target.value === "custom") {
      updateRow(index, { windowPreset: "custom" });
      return;
    }
    if (target.value === "all") {
      updateRow(index, { windowPreset: "all", dateStart: "", dateEnd: "" });
      return;
    }
    setRows((prev) =>
      prev.map((row, idx) => {
        if (idx !== index) return row;
        const anchor = anchorFor(row.productId, row.version || undefined);
        return {
          ...row,
          windowPreset: target.value,
          dateStart: isoDaysAgo(target.days, anchor),
          dateEnd: todayIso(anchor),
        };
      }),
    );
  }

  function applyTimePreset(presetValue: string): void {
    if (presetValue === "custom") {
      setTimeRow((prev) => ({ ...prev, presetValue: "custom" }));
      return;
    }
    setTimeRow((prev) => ({
      ...prev,
      presetValue,
      ...timeRowsFromPreset(presetValue, anchorFor(prev.productId)),
    }));
  }

  function addRow(): void {
    if (mode !== "multi_product") return;
    if (rows.length >= 5) return;
    setRows((prev) => [...prev, emptyRow()]);
  }

  function removeRow(index: number): void {
    setRows((prev) => prev.filter((_, idx) => idx !== index));
  }

  function handleSubmit(): void {
    if (mode === "same_product_time") {
      if (!timeRow.productId) {
        setError(t("errorPickProduct"));
        return;
      }
      const groups = timeRowToFilterGroups(timeRow, t("baselineWindow"), t("compareWindow"));
      if (groups.length < 2) {
        setError(t("errorInvalidWindow"));
        return;
      }
      setError("");
      onSubmit(mode, groups);
      return;
    }

    const groups = rows
      .map(rowToFilterGroup)
      .filter((group): group is CompareFilterGroup => Boolean(group));
    if (groups.length < 2) {
      setError(t("errorMinGroups"));
      return;
    }
    if (mode === "same_product_version") {
      const uniqueProducts = new Set(groups.map((g) => g.productId));
      if (uniqueProducts.size !== 1) {
        setError(t("errorSameProduct"));
        return;
      }
    }
    setError("");
    onSubmit(mode, groups);
  }

  function handleReset(): void {
    setError("");
    if (mode === "same_product_time") {
      setTimeRow(emptyTimeRow(firstProductId, anchorFor(firstProductId)));
    } else {
      setRows(rowsForMode(mode, firstProductId, t("baselineVersion"), t("compareVersion")));
    }
  }

  const canAddRow = mode === "multi_product" && rows.length < 5;

  return (
    <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-heading text-lg font-extrabold tracking-[-0.04em] text-ink">{t("filterConditions")}</h3>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(MODE_KEYS) as CompareMode[]).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => applyMode(option)}
              className={[
                "rounded-pill border px-3.5 py-1.5 text-sm font-semibold transition",
                mode === option
                  ? "border-transparent bg-ink text-white shadow-card"
                  : "border-line bg-white text-soft hover:text-ink",
              ].join(" ")}
            >
              {t(MODE_KEYS[option])}
            </button>
          ))}
        </div>
      </div>

      {mode === "same_product_time" ? (
        <TimeWindowEditor
          row={timeRow}
          productOptions={productOptions}
          productVersionsMap={productVersionsMap}
          onProductChange={(productId) =>
            setTimeRow((prev) => {
              const next: TimeRowState = { ...prev, productId, version: "" };
              if (prev.presetValue !== "custom") {
                Object.assign(next, timeRowsFromPreset(prev.presetValue, anchorFor(productId)));
              }
              return next;
            })
          }
          onVersionChange={(version) => setTimeRow((prev) => ({ ...prev, version }))}
          onPresetChange={applyTimePreset}
          onCustomChange={(patch) => setTimeRow((prev) => ({ ...prev, ...patch, presetValue: "custom" }))}
        />
      ) : (
        <div className="mt-4 space-y-3">
          {rows.map((row, index) => {
            const versionOptions = row.productId ? productVersionsMap.get(row.productId) ?? [] : [];
            const rangeLabel = row.productId ? rangeLabelFor(row.productId, row.version || undefined) : null;
            return (
              <div
                key={`row-${index}`}
                className="rounded-card border border-line bg-white px-4 py-3"
              >
                <div className="grid gap-3 md:grid-cols-[120px_1.6fr_1fr_1.2fr_auto]">
                  <div className="flex items-center text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                    {row.label || t("objectN", { index: index + 1 })}
                  </div>
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{t("product")}</div>
                    <select
                      value={row.productId}
                      onChange={(event) => updateRow(index, { productId: event.target.value, version: "" })}
                      className="mt-1 w-full rounded-card border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-[#f36f8f]"
                    >
                      <option value="">{t("selectProduct")}</option>
                      {productOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{t("version")}</div>
                    <select
                      value={row.version}
                      onChange={(event) => {
                        const newVersion = event.target.value;
                        const preset = PRESET_WINDOW_DAYS.find((p) => p.value === row.windowPreset);
                        if (preset && preset.days > 0) {
                          const anchor = anchorFor(row.productId, newVersion || undefined);
                          updateRow(index, {
                            version: newVersion,
                            dateStart: isoDaysAgo(preset.days, anchor),
                            dateEnd: todayIso(anchor),
                          });
                        } else {
                          updateRow(index, { version: newVersion });
                        }
                      }}
                      className="mt-1 w-full rounded-card border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-[#f36f8f]"
                      disabled={!row.productId}
                    >
                      <option value="">{t("allVersions")}</option>
                      {versionOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{t("reviewTime")}</div>
                    <div className="mt-1 flex gap-2">
                      <select
                        value={row.windowPreset}
                        onChange={(event) => applyPreset(index, event.target.value)}
                        className="rounded-card border border-line bg-white px-2 py-2 text-xs text-ink outline-none focus:border-[#f36f8f]"
                      >
                        {PRESET_WINDOW_DAYS.map((preset) => (
                          <option key={preset.value} value={preset.value}>
                            {t(preset.key)}
                          </option>
                        ))}
                      </select>
                      {row.windowPreset !== "all" ? (
                        <div className="flex flex-1 items-center gap-1 text-xs text-soft">
                          <input
                            type="date"
                            value={row.dateStart}
                            onChange={(event) =>
                              updateRow(index, { windowPreset: "custom", dateStart: event.target.value })
                            }
                            className="w-full rounded-card border border-line bg-white px-2 py-2 text-xs outline-none focus:border-[#f36f8f]"
                          />
                          <span>~</span>
                          <input
                            type="date"
                            value={row.dateEnd}
                            onChange={(event) =>
                              updateRow(index, { windowPreset: "custom", dateEnd: event.target.value })
                            }
                            className="w-full rounded-card border border-line bg-white px-2 py-2 text-xs outline-none focus:border-[#f36f8f]"
                          />
                        </div>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex items-end justify-end">
                    {mode === "multi_product" ? (
                      <button
                        type="button"
                        onClick={() => removeRow(index)}
                        disabled={rows.length <= 2}
                        className="rounded-pill border border-line bg-white px-3 py-1.5 text-xs font-semibold text-soft transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {tCommon("remove")}
                      </button>
                    ) : null}
                  </div>
                </div>
                {rangeLabel ? (
                  <div className="mt-2 text-[11px] text-soft">{rangeLabel}</div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      {error ? (
        <div className="mt-3 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-2 text-sm text-[#b44655]">
          {error}
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-soft">
          {mode === "same_product_time"
            ? (() => {
                const b1 = timeRow.baselineStart || "…";
                const b2 = timeRow.baselineEnd || "…";
                const c1 = timeRow.compareStart || "…";
                const c2 = timeRow.compareEnd || "…";
                const rangeText = rangeLabelFor(timeRow.productId);
                return rangeText
                  ? t("windowSummaryWithRange", { b1, b2, c1, c2, range: rangeText })
                  : t("windowSummary", { b1, b2, c1, c2 });
              })()
            : mode === "same_product_version"
              ? t("sameProductInfo")
              : t("objectCountFormat", { count: rows.length })}
        </div>
        <div className="flex gap-2">
          {canAddRow ? (
            <button
              type="button"
              onClick={addRow}
              className="rounded-pill border border-line bg-white px-4 py-2 text-sm font-semibold text-ink"
            >
              {t("addObject")}
            </button>
          ) : null}
          <button
            type="button"
            onClick={handleReset}
            className="rounded-pill border border-line bg-white px-4 py-2 text-sm font-semibold text-soft"
          >
            {tCommon("reset")}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="rounded-pill bg-ink px-5 py-2 text-sm font-semibold text-white shadow-card disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? tCommon("generating") : t("generateBtn")}
          </button>
        </div>
      </div>
    </section>
  );
}

type TimeWindowEditorProps = {
  row: TimeRowState;
  productOptions: Array<{ value: string; label: string; versions: string[] }>;
  productVersionsMap: Map<string, string[]>;
  onProductChange: (productId: string) => void;
  onVersionChange: (version: string) => void;
  onPresetChange: (preset: string) => void;
  onCustomChange: (patch: Partial<Pick<TimeRowState, "baselineStart" | "baselineEnd" | "compareStart" | "compareEnd">>) => void;
};

function TimeWindowEditor({
  row,
  productOptions,
  productVersionsMap,
  onProductChange,
  onVersionChange,
  onPresetChange,
  onCustomChange,
}: TimeWindowEditorProps) {
  const t = useTranslations("analysis.compare");
  const versionOptions = row.productId ? productVersionsMap.get(row.productId) ?? [] : [];
  const isCustom = row.presetValue === "custom";

  return (
    <div className="mt-4 space-y-3">
      <div className="grid gap-3 rounded-card border border-line bg-white px-4 py-3 md:grid-cols-[1.6fr_1fr_1.2fr]">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{t("product")}</div>
          <select
            value={row.productId}
            onChange={(event) => onProductChange(event.target.value)}
            className="mt-1 w-full rounded-card border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-[#f36f8f]"
          >
            <option value="">{t("selectProduct")}</option>
            {productOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{t("version")}</div>
          <select
            value={row.version}
            onChange={(event) => onVersionChange(event.target.value)}
            className="mt-1 w-full rounded-card border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-[#f36f8f]"
            disabled={!row.productId}
          >
            <option value="">{t("allVersions")}</option>
            {versionOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{t("timeBaseMetric")}</div>
          <select
            value={row.presetValue}
            onChange={(event) => onPresetChange(event.target.value)}
            className="mt-1 w-full rounded-card border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-[#f36f8f]"
          >
            {TIME_PRESET_DAYS.map((preset) => (
              <option key={preset.value} value={preset.value}>
                {t(preset.key)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isCustom ? (
        <div className="grid gap-3 rounded-card border border-line bg-white px-4 py-3 md:grid-cols-2">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{t("baselineWindow")}</div>
            <div className="mt-1 flex items-center gap-1 text-xs text-soft">
              <input
                type="date"
                value={row.baselineStart}
                onChange={(event) => onCustomChange({ baselineStart: event.target.value })}
                className="w-full rounded-card border border-line bg-white px-2 py-2 text-xs outline-none focus:border-[#f36f8f]"
              />
              <span>~</span>
              <input
                type="date"
                value={row.baselineEnd}
                onChange={(event) => onCustomChange({ baselineEnd: event.target.value })}
                className="w-full rounded-card border border-line bg-white px-2 py-2 text-xs outline-none focus:border-[#f36f8f]"
              />
            </div>
          </div>
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">{t("compareWindow")}</div>
            <div className="mt-1 flex items-center gap-1 text-xs text-soft">
              <input
                type="date"
                value={row.compareStart}
                onChange={(event) => onCustomChange({ compareStart: event.target.value })}
                className="w-full rounded-card border border-line bg-white px-2 py-2 text-xs outline-none focus:border-[#f36f8f]"
              />
              <span>~</span>
              <input
                type="date"
                value={row.compareEnd}
                onChange={(event) => onCustomChange({ compareEnd: event.target.value })}
                className="w-full rounded-card border border-line bg-white px-2 py-2 text-xs outline-none focus:border-[#f36f8f]"
              />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export type { CompareMode };
