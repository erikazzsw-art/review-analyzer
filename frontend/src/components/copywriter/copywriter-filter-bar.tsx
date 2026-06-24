"use client";

import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { Calendar } from "lucide-react";

import { ProductSearchCombobox } from "@/components/analysis/product-search-combobox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchProductVersions } from "@/lib/api/browser";
import type { CopywriterProductVersion } from "@/lib/api/types";

type Props = {
  productId: string;
  version: string;
  range: string;
  platform: string;
};

const RANGE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "all", label: "全部时间" },
  { value: "7d", label: "最近 7 天" },
  { value: "14d", label: "最近 14 天" },
  { value: "30d", label: "最近 30 天" },
  { value: "90d", label: "最近 90 天" },
];

const VERSION_ALL = "";

export function CopywriterFilterBar({ productId, version, range, platform }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [, startTransition] = useTransition();

  const [versions, setVersions] = useState<CopywriterProductVersion[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);

  useEffect(() => {
    if (!productId) {
      setVersions([]);
      return;
    }
    const ctl = new AbortController();
    setVersionsLoading(true);
    fetchProductVersions(productId)
      .then((res) => {
        if (ctl.signal.aborted) return;
        setVersions(res.items);
      })
      .catch(() => {
        if (!ctl.signal.aborted) setVersions([]);
      })
      .finally(() => {
        if (!ctl.signal.aborted) setVersionsLoading(false);
      });
    return () => ctl.abort();
  }, [productId]);

  const pushParams = useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(params.toString());
      Object.entries(patch).forEach(([k, v]) => {
        if (v === null || v === "") next.delete(k);
        else next.set(k, v);
      });
      startTransition(() => {
        router.push(`${pathname}?${next.toString()}`);
      });
    },
    [params, pathname, router],
  );

  const handleProductChange = (pid: string) => {
    if (!pid || pid === productId) return;
    pushParams({ product_id: pid, version: null });
  };

  const handleVersionChange = (value: string) => {
    pushParams({ version: value === VERSION_ALL ? null : value });
  };

  const handleRangeChange = (value: string) => {
    pushParams({ range: value === "all" ? null : value });
  };

  const singleVersion = versions.length === 1;
  const singleVersionLabel = singleVersion ? `显示全部版本（${versions[0].version}）` : "";

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-shell border border-line bg-white/84 px-4 py-3 shadow-card backdrop-blur">
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-soft">产品</span>
        <ProductSearchCombobox value={productId} onChange={handleProductChange} placeholder="搜索产品编码" />
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-soft">版本</span>
        {versionsLoading ? (
          <div className="flex h-9 w-44 items-center rounded-pill border border-line bg-white px-3 text-sm text-soft">
            加载版本…
          </div>
        ) : !productId ? (
          <div className="flex h-9 w-44 items-center rounded-pill border border-dashed border-line bg-white/60 px-3 text-sm text-soft">
            先选择产品
          </div>
        ) : singleVersion ? (
          <div className="flex h-9 w-44 items-center rounded-pill border border-line bg-[#faf8fb] px-3 text-sm font-medium text-soft">
            {singleVersionLabel}
          </div>
        ) : (
          <Select value={version || VERSION_ALL} onValueChange={handleVersionChange}>
            <SelectTrigger className="h-9 w-44 rounded-pill border-line bg-white text-sm font-medium">
              <SelectValue placeholder="全部版本" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={VERSION_ALL}>全部版本</SelectItem>
              {versions.map((item) => (
                <SelectItem key={item.version} value={item.version}>
                  {item.version} · {item.review_count} 条
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-soft">时间</span>
        <Select value={range || "all"} onValueChange={handleRangeChange}>
          <SelectTrigger className="h-9 w-44 rounded-pill border-line bg-white text-sm font-medium">
            <Calendar className="mr-1 h-3.5 w-3.5 text-soft" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {RANGE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-soft">平台</span>
        <div className="flex h-9 items-center rounded-pill border border-line bg-white px-3 text-sm font-medium text-ink">
          {PLATFORM_LABEL[platform] || platform}
        </div>
      </div>
    </div>
  );
}

const PLATFORM_LABEL: Record<string, string> = {
  amazon: "📦 亚马逊",
  facebook: "👤 Facebook",
  tiktok: "🎵 TikTok",
  walmart: "🏬 沃尔玛",
  google: "🔍 Google",
  instagram: "📷 Instagram",
};
