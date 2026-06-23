"use client";

import { useEffect, useMemo, useState } from "react";

import type { CompareFilterGroup, ProductOverview } from "@/lib/api/types";

type CompareMode = "same_product_time" | "same_product_version" | "multi_product" | "custom";

type CompareFilterBarProps = {
  products: ProductOverview[];
  initialMode?: CompareMode;
  initialGroups?: CompareFilterGroup[];
  isSubmitting?: boolean;
  onSubmit: (mode: CompareMode, groups: CompareFilterGroup[]) => void;
};

const MODE_LABELS: Record<CompareMode, string> = {
  same_product_time: "时间环比",
  same_product_version: "版本对比",
  multi_product: "多产品对比",
  custom: "自定义对比",
};

const PRESET_WINDOWS: Array<{ value: string; label: string; days: number }> = [
  { value: "7d", label: "过去 7 天", days: 7 },
  { value: "14d", label: "过去 14 天", days: 14 },
  { value: "30d", label: "过去 30 天", days: 30 },
  { value: "60d", label: "过去 60 天", days: 60 },
  { value: "180d", label: "过去 180 天", days: 180 },
  { value: "all", label: "全部时间", days: 0 },
  { value: "custom", label: "自定义", days: -1 },
];

function isoDaysAgo(days: number): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() - days);
  return date.toISOString().slice(0, 10);
}

function todayIso(): string {
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

function rowsForMode(mode: CompareMode, productId: string): RowState[] {
  if (mode === "same_product_time") {
    return [
      {
        productId,
        version: "",
        windowPreset: "30d",
        dateStart: isoDaysAgo(60),
        dateEnd: isoDaysAgo(31),
        label: "基准窗口",
      },
      {
        productId,
        version: "",
        windowPreset: "30d",
        dateStart: isoDaysAgo(30),
        dateEnd: todayIso(),
        label: "对比窗口",
      },
    ];
  }
  if (mode === "same_product_version") {
    return [
      { ...emptyRow(), productId, label: "基准版本" },
      { ...emptyRow(), productId, label: "对比版本" },
    ];
  }
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

export function CompareFilterBar({
  products,
  initialMode = "same_product_time",
  initialGroups,
  isSubmitting,
  onSubmit,
}: CompareFilterBarProps) {
  const [mode, setMode] = useState<CompareMode>(initialMode);
  const firstProductId = products[0]?.parent_product_id ?? "";
  const [rows, setRows] = useState<RowState[]>(() => {
    if (initialGroups && initialGroups.length > 0) {
      return initialGroups.map((group) => ({
        productId: group.productId,
        version: group.versions[0] ?? "",
        windowPreset: "custom",
        dateStart: group.dateStart ?? isoDaysAgo(30),
        dateEnd: group.dateEnd ?? todayIso(),
        label: group.label ?? "",
      }));
    }
    return rowsForMode(initialMode, firstProductId);
  });
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (!rows.some((row) => row.productId) && firstProductId) {
      setRows((prev) =>
        prev.map((row) => (row.productId ? row : { ...row, productId: firstProductId })),
      );
    }
  }, [firstProductId, rows]);

  const productOptions = useMemo(
    () =>
      products.map((product) => ({
        value: product.parent_product_id,
        label: product.name
          ? `${product.parent_product_id} · ${product.name}`
          : product.parent_product_id,
        versions: product.versions
          .map((version) => version.version_name)
          .filter((value): value is string => Boolean(value)),
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
    setRows(rowsForMode(nextMode, firstProductId));
    setError("");
  }

  function updateRow(index: number, patch: Partial<RowState>): void {
    setRows((prev) => prev.map((row, idx) => (idx === index ? { ...row, ...patch } : row)));
  }

  function applyPreset(index: number, preset: string): void {
    const target = PRESET_WINDOWS.find((item) => item.value === preset);
    if (!target) return;
    if (target.value === "custom") {
      updateRow(index, { windowPreset: "custom" });
      return;
    }
    if (target.value === "all") {
      updateRow(index, { windowPreset: "all", dateStart: "", dateEnd: "" });
      return;
    }
    updateRow(index, {
      windowPreset: target.value,
      dateStart: isoDaysAgo(target.days),
      dateEnd: todayIso(),
    });
  }

  function addRow(): void {
    if (mode === "same_product_time" || mode === "same_product_version") return;
    if (rows.length >= 5) return;
    setRows((prev) => [...prev, emptyRow()]);
  }

  function removeRow(index: number): void {
    setRows((prev) => prev.filter((_, idx) => idx !== index));
  }

  function handleSubmit(): void {
    const groups = rows.map(rowToFilterGroup).filter((group): group is CompareFilterGroup => Boolean(group));
    if (groups.length < 2) {
      setError("至少需要 2 个有效的对比对象（请选择产品）。");
      return;
    }
    if (mode === "same_product_time" || mode === "same_product_version") {
      const uniqueProducts = new Set(groups.map((g) => g.productId));
      if (uniqueProducts.size !== 1) {
        setError("当前模式下所有对比对象必须是同一个产品。");
        return;
      }
    }
    setError("");
    onSubmit(mode, groups);
  }

  function handleReset(): void {
    setRows(rowsForMode(mode, firstProductId));
    setError("");
  }

  const canAddRow = mode !== "same_product_time" && mode !== "same_product_version" && rows.length < 5;

  return (
    <section className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-heading text-lg font-extrabold tracking-[-0.04em] text-ink">筛选条件</h3>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(MODE_LABELS) as CompareMode[]).map((option) => (
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
              {MODE_LABELS[option]}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {rows.map((row, index) => {
          const versionOptions = row.productId ? productVersionsMap.get(row.productId) ?? [] : [];
          return (
            <div
              key={`row-${index}`}
              className="grid gap-3 rounded-card border border-line bg-white px-4 py-3 md:grid-cols-[120px_1.6fr_1fr_1.2fr_auto]"
            >
              <div className="flex items-center text-xs font-semibold uppercase tracking-[0.1em] text-soft">
                {row.label || `对象 ${index + 1}`}
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">产品</div>
                <select
                  value={row.productId}
                  onChange={(event) => updateRow(index, { productId: event.target.value, version: "" })}
                  className="mt-1 w-full rounded-card border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-[#f36f8f]"
                >
                  <option value="">选择产品</option>
                  {productOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">版本</div>
                <select
                  value={row.version}
                  onChange={(event) => updateRow(index, { version: event.target.value })}
                  className="mt-1 w-full rounded-card border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-[#f36f8f]"
                  disabled={!row.productId}
                >
                  <option value="">全部版本</option>
                  {versionOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-soft">评论时间</div>
                <div className="mt-1 flex gap-2">
                  <select
                    value={row.windowPreset}
                    onChange={(event) => applyPreset(index, event.target.value)}
                    className="rounded-card border border-line bg-white px-2 py-2 text-xs text-ink outline-none focus:border-[#f36f8f]"
                  >
                    {PRESET_WINDOWS.map((preset) => (
                      <option key={preset.value} value={preset.value}>
                        {preset.label}
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
                {mode === "multi_product" || mode === "custom" ? (
                  <button
                    type="button"
                    onClick={() => removeRow(index)}
                    disabled={rows.length <= 2}
                    className="rounded-pill border border-line bg-white px-3 py-1.5 text-xs font-semibold text-soft transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    移除
                  </button>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      {error ? (
        <div className="mt-3 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-2 text-sm text-[#b44655]">
          {error}
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs text-soft">
          {mode === "same_product_time"
            ? "同一产品 · 两个时间窗口对比"
            : mode === "same_product_version"
              ? "同一产品 · 不同版本对比（时间窗口共用）"
              : `${rows.length} 个对比对象（最多 5 个）`}
        </div>
        <div className="flex gap-2">
          {canAddRow ? (
            <button
              type="button"
              onClick={addRow}
              className="rounded-pill border border-line bg-white px-4 py-2 text-sm font-semibold text-ink"
            >
              + 加一个对比对象
            </button>
          ) : null}
          <button
            type="button"
            onClick={handleReset}
            className="rounded-pill border border-line bg-white px-4 py-2 text-sm font-semibold text-soft"
          >
            重置
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="rounded-pill bg-ink px-5 py-2 text-sm font-semibold text-white shadow-card disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "生成中..." : "生成对比"}
          </button>
        </div>
      </div>
    </section>
  );
}

export type { CompareMode };
