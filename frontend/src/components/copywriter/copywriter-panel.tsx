"use client";

import { useEffect, useMemo, useState } from "react";

import { fetchCopywriterPlatforms, generateCopywriter } from "@/lib/api/browser";
import type {
  CopywriterGeneratedItem,
  CopywriterPlatform,
  CopywriterProduct,
} from "@/lib/api/types";

type CopywriterPanelProps = {
  sessions: CopywriterProduct[];
};

const STYLES = ["简洁专业", "幽默风趣", "情感共鸣", "数据驱动"];

export function CopywriterPanel({ sessions }: CopywriterPanelProps) {
  const [platforms, setPlatforms] = useState<CopywriterPlatform[]>([]);
  const [activePlatform, setActivePlatform] = useState("amazon");
  const [selectedSessionIds, setSelectedSessionIds] = useState<number[]>([]);
  const [featuresText, setFeaturesText] = useState("");
  const [generateAdCopy, setGenerateAdCopy] = useState(true);
  const [generateIdealDesc, setGenerateIdealDesc] = useState(true);
  const [styleByType, setStyleByType] = useState<Record<string, string>>({});
  const [generatedItems, setGeneratedItems] = useState<CopywriterGeneratedItem[]>([]);
  const [reviewSummary, setReviewSummary] = useState("");
  const [idealProfileSummary, setIdealProfileSummary] = useState("");
  const [idealProfileFeatures, setIdealProfileFeatures] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchCopywriterPlatforms()
      .then((items) => {
        setPlatforms(items);
        if (items.length > 0) {
          setActivePlatform(items[0].id);
          const defaultStyles: Record<string, string> = {};
          items[0].types.forEach((item) => {
            defaultStyles[item.id] = STYLES[0];
          });
          setStyleByType(defaultStyles);
        }
      })
      .catch((err) => {
        const candidate = err as { message?: string };
        setError(candidate.message || "加载平台失败");
      });
  }, []);

  const activePlatformData = useMemo(
    () => platforms.find((item) => item.id === activePlatform) || null,
    [activePlatform, platforms],
  );

  function toggleSession(sessionId: number): void {
    setSelectedSessionIds((current) =>
      current.includes(sessionId)
        ? current.filter((value) => value !== sessionId)
        : [...current, sessionId],
    );
  }

  async function handleGenerate(): Promise<void> {
    if (selectedSessionIds.length === 0) {
      setError("请先选择至少一个分析批次。");
      return;
    }

    setError("");
    setIsSubmitting(true);
    try {
      const response = await generateCopywriter({
        productSessionIds: selectedSessionIds,
        platform: activePlatform,
        featuresText: featuresText.trim(),
        generateAdCopy,
        generateIdealDesc,
        styleByType,
      });
      setGeneratedItems(response.generated_items);
      setReviewSummary(response.review_summary);
      setIdealProfileSummary(response.ideal_profile?.summary || "");
      setIdealProfileFeatures(response.ideal_profile?.features || []);
    } catch (err) {
      const candidate = err as { message?: string };
      setError(candidate.message || "生成失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
      <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
          COPYWRITER
        </div>
        <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          选择产品批次并生成文案
        </h2>
        <p className="mt-3 text-sm leading-7 text-soft">
          先勾选分析批次，再选择投放平台。系统会基于评论摘要和功能点生成广告文案与理想产品画像。
        </p>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {sessions.map((group) => (
            <div key={group.product_id} className="rounded-card border border-line bg-white px-4 py-4">
              <div className="text-sm font-semibold text-ink">
                {group.product_name || group.product_id}
              </div>
              <div className="mt-2 space-y-2">
                {group.sessions.map((session) => {
                  const isActive = selectedSessionIds.includes(session.session_id);
                  return (
                    <button
                      key={session.session_id}
                      type="button"
                      onClick={() => toggleSession(session.session_id)}
                      className={[
                        "w-full rounded-card border px-4 py-3 text-left text-sm transition",
                        isActive
                          ? "border-transparent bg-ink text-white shadow-card"
                          : "border-line bg-white text-ink hover:border-[#f36f8f]",
                      ].join(" ")}
                    >
                      <div className="font-semibold">{session.label}</div>
                      <div className={["mt-1 text-xs", isActive ? "text-white/80" : "text-soft"].join(" ")}>
                        {session.version} · {session.total_reviews} 条 · 差评 {session.negative_count}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6">
          <div className="text-sm font-semibold text-ink">投放平台</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {platforms.map((platform) => {
              const isActive = activePlatform === platform.id;
              return (
                <button
                  key={platform.id}
                  type="button"
                  onClick={() => {
                    setActivePlatform(platform.id);
                    const next: Record<string, string> = {};
                    platform.types.forEach((item) => {
                      next[item.id] = styleByType[item.id] || STYLES[0];
                    });
                    setStyleByType(next);
                  }}
                  className={[
                    "rounded-pill border px-4 py-2 text-sm font-semibold transition",
                    isActive
                      ? "border-transparent bg-ink text-white shadow-card"
                      : "border-line bg-white text-soft hover:text-ink",
                  ].join(" ")}
                >
                  {platform.icon} {platform.label_zh}
                </button>
              );
            })}
          </div>
        </div>

        <label className="mt-6 block space-y-2">
          <span className="text-sm font-semibold text-ink">产品功能点</span>
          <textarea
            value={featuresText}
            onChange={(event) => setFeaturesText(event.target.value)}
            className="min-h-28 w-full rounded-card border border-line bg-white px-4 py-3 text-sm outline-none transition focus:border-[#f36f8f]"
            placeholder="例如：主动降噪、12 小时续航、IPX5 防水..."
          />
        </label>

        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="flex items-center gap-3 rounded-card border border-line bg-white px-4 py-4 text-sm text-ink">
            <input
              type="checkbox"
              checked={generateAdCopy}
              onChange={(event) => setGenerateAdCopy(event.target.checked)}
            />
            生成广告文案
          </label>
          <label className="flex items-center gap-3 rounded-card border border-line bg-white px-4 py-4 text-sm text-ink">
            <input
              type="checkbox"
              checked={generateIdealDesc}
              onChange={(event) => setGenerateIdealDesc(event.target.checked)}
            />
            生成理想产品画像
          </label>
        </div>

        {activePlatformData ? (
          <div className="mt-6 rounded-card border border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
            <div className="font-semibold text-ink">{activePlatformData.name_zh}</div>
            <div className="mt-2">{activePlatformData.guidelines_zh}</div>
          </div>
        ) : null}

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={isSubmitting || selectedSessionIds.length === 0}
            className="inline-flex min-h-12 items-center justify-center rounded-pill bg-ink px-6 py-3 text-sm font-semibold text-white shadow-card disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "生成中..." : "生成文案"}
          </button>
        </div>

        {error ? (
          <div className="mt-4 rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]">
            {error}
          </div>
        ) : null}
      </div>

      <div className="space-y-6">
        <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            OUTPUT
          </div>
          <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            生成结果
          </h3>
          <p className="mt-2 text-sm leading-7 text-soft">
            结果会展示英文文案、中文参考和合规状态。不同广告类型可单独切换风格。
          </p>

          {generatedItems.length > 0 ? (
            <div className="mt-5 space-y-4">
              {generatedItems.map((item) => (
                <div key={item.type_id} className="rounded-card border border-line bg-white px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-semibold text-ink">
                      {item.type_name} · {item.char_count}/{item.limit}
                    </div>
                    <span className={[
                      "rounded-pill px-3 py-1 text-xs font-bold",
                      item.compliant ? "bg-[#e8f8f0] text-[#3d8b74]" : "bg-[#fff3f5] text-[#b44655]",
                    ].join(" ")}>
                      {item.compliant ? "✓ 合规" : "⚠ 风险"}
                    </span>
                  </div>
                  <div className="mt-3 text-sm leading-7 text-ink whitespace-pre-line">{item.en}</div>
                  <div className="mt-3 text-xs leading-6 text-soft">
                    中文参考：{item.zh || "—"}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {STYLES.map((style) => (
                      <button
                        key={`${item.type_id}-${style}`}
                        type="button"
                        onClick={() => setStyleByType((current) => ({ ...current, [item.type_id]: style }))}
                        className={[
                          "rounded-pill border px-3 py-1 text-xs font-semibold transition",
                          (styleByType[item.type_id] || STYLES[0]) === style
                            ? "border-transparent bg-ink text-white"
                            : "border-line bg-white text-soft hover:text-ink",
                        ].join(" ")}
                      >
                        {style}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-5 rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
              还没有生成结果。先选择批次、平台和功能点，再点击生成。
            </div>
          )}
        </section>

        <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            INSIGHT
          </div>
          <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            理想产品画像
          </h3>
          {idealProfileFeatures.length > 0 ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {idealProfileFeatures.map((feature) => (
                <span key={feature} className="rounded-pill bg-[#fff1f5] px-3 py-1 text-xs font-semibold text-[#d94d72]">
                  {feature}
                </span>
              ))}
            </div>
          ) : null}
          <p className="mt-4 text-sm leading-7 text-soft whitespace-pre-line">
            {idealProfileSummary || "生成后会在这里看到客户的理想画像摘要。"}
          </p>
          {reviewSummary ? (
            <div className="mt-4 rounded-card border border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft whitespace-pre-line">
              {reviewSummary}
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}
