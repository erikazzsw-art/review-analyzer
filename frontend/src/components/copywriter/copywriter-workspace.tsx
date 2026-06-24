"use client";

import { useEffect, useMemo, useState } from "react";

import {
  fetchCopywriterPlatforms,
  fetchCopywriterStyles,
  generateCopywriter,
} from "@/lib/api/browser";
import type {
  CopywriterGeneratedItem,
  CopywriterIdealProfile,
  CopywriterPlatform,
  CopywriterPlatformType,
  CopywriterStyle,
} from "@/lib/api/types";

import { CopywriterFilterBar } from "@/components/copywriter/copywriter-filter-bar";
import { CopywriterResultsGrid } from "@/components/copywriter/copywriter-results-grid";
import { IdealProfileCard } from "@/components/copywriter/ideal-profile-card";

type Props = {
  productId: string;
  version: string;
  range: string;
  platform: string;
  style: string;
};

const PLATFORM_ORDER = ["amazon", "facebook", "tiktok", "walmart", "google", "instagram"];
const DEFAULT_STYLE = "简洁专业";

export function CopywriterWorkspace({
  productId,
  version,
  range,
  platform: platformFromUrl,
  style: styleFromUrl,
}: Props) {
  const [platforms, setPlatforms] = useState<CopywriterPlatform[]>([]);
  const [styles, setStyles] = useState<CopywriterStyle[]>([]);
  const [activePlatformId, setActivePlatformId] = useState(platformFromUrl || PLATFORM_ORDER[0]);
  const [activeStyle, setActiveStyle] = useState(styleFromUrl || DEFAULT_STYLE);
  const [featuresText, setFeaturesText] = useState("");
  const [generatedItems, setGeneratedItems] = useState<CopywriterGeneratedItem[]>([]);
  const [idealProfile, setIdealProfile] = useState<CopywriterIdealProfile | null>(null);
  const [reviewCount, setReviewCount] = useState(0);
  const [busy, setBusy] = useState<"idle" | "generate" | "regen-profile" | string>("idle");
  const [error, setError] = useState("");
  const [loadingMeta, setLoadingMeta] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchCopywriterPlatforms(), fetchCopywriterStyles()])
      .then(([platformList, styleList]) => {
        if (cancelled) return;
        const ordered = [...platformList].sort(
          (a, b) =>
            PLATFORM_ORDER.indexOf(a.id) - PLATFORM_ORDER.indexOf(b.id),
        );
        setPlatforms(ordered);
        setStyles(styleList);
        if (ordered.length > 0 && !ordered.find((p) => p.id === activePlatformId)) {
          setActivePlatformId(ordered[0].id);
        }
        setLoadingMeta(false);
      })
      .catch((err) => {
        if (cancelled) return;
        const candidate = err as { message?: string };
        setError(candidate.message || "加载平台/风格失败");
        setLoadingMeta(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activePlatform = useMemo(
    () => platforms.find((p) => p.id === activePlatformId) || null,
    [platforms, activePlatformId],
  );

  const incompatibleSet = useMemo(() => {
    const map: Record<string, string[]> = {};
    styles.forEach((s) => {
      map[s.name] = s.incompatible_on || [];
    });
    return map;
  }, [styles]);

  function isStyleCompatible(styleName: string): boolean {
    return !(incompatibleSet[styleName] || []).includes(activePlatformId);
  }

  function handlePlatformSwitch(id: string): void {
    setActivePlatformId(id);
    if (!isStyleCompatibleFor(activeStyle, id)) {
      setActiveStyle(DEFAULT_STYLE);
    }
    setGeneratedItems([]);
    setError("");
  }

  function isStyleCompatibleFor(styleName: string, platformId: string): boolean {
    return !(incompatibleSet[styleName] || []).includes(platformId);
  }

  async function runGenerate(opts: {
    adTypeId?: string | null;
    append?: boolean;
    forceRegenProfile?: boolean;
    label: string;
  }): Promise<void> {
    if (!productId) {
      setError("请先选择产品。");
      return;
    }
    if (!isStyleCompatible(activeStyle)) {
      setError(`当前平台不允许风格 “${activeStyle}”。`);
      return;
    }
    setError("");
    setBusy(opts.label);
    try {
      const response = await generateCopywriter({
        productId,
        version: version || null,
        range: range || "all",
        platform: activePlatformId,
        adTypeId: opts.adTypeId ?? null,
        style: activeStyle,
        nVariants: 1,
        featuresText: featuresText.trim(),
        generateAdCopy: true,
        generateIdealDesc: !opts.adTypeId, // 单条重生时不重算 profile
        forceRegenProfile: opts.forceRegenProfile ?? false,
      });
      setReviewCount(response.review_count);
      if (opts.append) {
        setGeneratedItems((prev) => [...prev, ...response.generated_items]);
      } else {
        setGeneratedItems(response.generated_items);
      }
      if (response.ideal_profile) {
        setIdealProfile(response.ideal_profile);
      }
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "生成失败");
    } finally {
      setBusy("idle");
    }
  }

  async function handleRegenProfile(): Promise<void> {
    await runGenerate({ label: "regen-profile", forceRegenProfile: true, append: false });
  }

  if (loadingMeta) {
    return (
      <div className="rounded-shell border border-line bg-white/84 px-6 py-10 text-sm text-soft shadow-card">
        正在加载平台与风格…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <CopywriterFilterBar
        productId={productId}
        version={version}
        range={range}
        platform={activePlatformId}
      />

      {/* 平台 Tab */}
      <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
          COPYWRITER
        </div>
        <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          选择投放平台并生成文案
        </h2>
        <p className="mt-3 text-sm leading-7 text-soft">
          系统会基于该产品（选定版本与时间窗）的评论分析结果生成符合平台规则的英文文案与中文参考。
        </p>

        <div className="mt-5 flex flex-wrap gap-2">
          {platforms.map((p) => {
            const isActive = p.id === activePlatformId;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => handlePlatformSwitch(p.id)}
                className={[
                  "rounded-pill border px-4 py-2 text-sm font-semibold transition",
                  isActive
                    ? "border-transparent bg-ink text-white shadow-card"
                    : "border-line bg-white text-soft hover:text-ink",
                ].join(" ")}
              >
                {p.icon} {p.label_zh}
              </button>
            );
          })}
        </div>

        {activePlatform ? (
          <PlatformRulePanel platform={activePlatform} />
        ) : null}

        <label className="mt-5 block space-y-2">
          <span className="text-sm font-semibold text-ink">产品功能点（可选，告诉模型重点突出哪些卖点）</span>
          <textarea
            value={featuresText}
            onChange={(e) => setFeaturesText(e.target.value)}
            className="min-h-24 w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            placeholder="例如：主动降噪、12 小时续航、IPX5 防水…"
          />
        </label>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          {error ? (
            <span className="text-sm text-[#b44655]">{error}</span>
          ) : (
            <span className="text-xs text-soft">
              {reviewCount > 0 ? `本次生成基于 ${reviewCount} 条评论` : "选好平台与风格后点击生成"}
            </span>
          )}
          <button
            type="button"
            disabled={busy !== "idle" || !productId || !isStyleCompatible(activeStyle)}
            onClick={() => runGenerate({ label: "generate", append: false })}
            className="inline-flex min-h-10 items-center justify-center rounded-pill bg-ink px-5 py-2 text-sm font-semibold text-white shadow-card disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy === "generate" ? "生成中…" : "生成文案"}
          </button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <CopywriterResultsGrid
          platform={activePlatform}
          styles={styles}
          activeStyle={activeStyle}
          onStyleChange={(s) => {
            if (!isStyleCompatibleFor(s, activePlatformId)) return;
            setActiveStyle(s);
          }}
          items={generatedItems}
          onAppend={(adTypeId) =>
            runGenerate({ adTypeId, append: true, label: `append:${adTypeId}` })
          }
          onReplace={(adTypeId) =>
            runGenerate({ adTypeId, append: false, label: `replace:${adTypeId}` })
          }
          busy={busy}
        />

        <IdealProfileCard
          profile={idealProfile}
          loading={busy === "regen-profile"}
          onRegenerate={productId ? handleRegenProfile : undefined}
        />
      </div>
    </div>
  );
}

function PlatformRulePanel({ platform }: { platform: CopywriterPlatform }) {
  const hasEstimate = platform.types.some((t) => t.internal_estimate);
  return (
    <div className="mt-5 rounded-card border border-line bg-[#fffafb] px-4 py-4">
      <div className="text-sm font-semibold text-ink">广告类型与字符限制</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {platform.types.map((t) => (
          <span
            key={t.id}
            className="rounded-pill bg-white px-3 py-1 text-xs font-semibold text-ink shadow-sm"
          >
            {t.name_zh} · {t.limit} 字符
            {t.internal_estimate ? " *" : ""}
          </span>
        ))}
      </div>
      <div className="mt-3 text-xs leading-6 text-soft">{platform.guidelines_zh}</div>
      {hasEstimate ? (
        <div className="mt-2 text-xs text-[#b44655]">
          * 该平台部分字符位为内部保守估计，发布前请二次核对官方文档。
        </div>
      ) : null}
    </div>
  );
}

export type { CopywriterPlatformType };
