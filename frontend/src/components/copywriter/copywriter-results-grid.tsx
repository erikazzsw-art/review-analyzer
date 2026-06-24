"use client";

import { useState } from "react";
import { ClipboardCopy } from "lucide-react";

import type {
  CopywriterGeneratedItem,
  CopywriterPlatform,
  CopywriterStyle,
} from "@/lib/api/types";

type Props = {
  platform: CopywriterPlatform | null;
  styles: CopywriterStyle[];
  activeStyle: string;
  onStyleChange: (style: string) => void;
  items: CopywriterGeneratedItem[];
  onAppend: (adTypeId: string) => void;
  onReplace: (adTypeId: string) => void;
  busy: string;
};

export function CopywriterResultsGrid({
  platform,
  styles,
  activeStyle,
  onStyleChange,
  items,
  onAppend,
  onReplace,
  busy,
}: Props) {
  const grouped = groupByType(items);
  const hasItems = items.length > 0;
  const platformId = platform?.id || "";

  return (
    <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            OUTPUT
          </div>
          <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            生成结果
          </h3>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {styles.map((s) => {
            const disabled = (s.incompatible_on || []).includes(platformId);
            const isActive = s.name === activeStyle && !disabled;
            return (
              <button
                key={s.name}
                type="button"
                disabled={disabled}
                title={
                  disabled
                    ? `“${s.name}” 在该平台被禁用（参见平台规则）`
                    : ""
                }
                onClick={() => onStyleChange(s.name)}
                className={[
                  "rounded-pill border px-3 py-1.5 text-xs font-semibold transition",
                  disabled
                    ? "cursor-not-allowed border-line bg-[#f6f5f7] text-[#bcb8c3]"
                    : isActive
                      ? "border-transparent bg-ink text-white shadow-card"
                      : "border-line bg-white text-soft hover:text-ink",
                ].join(" ")}
              >
                {s.name}
              </button>
            );
          })}
        </div>
      </div>

      {!hasItems ? (
        <div className="mt-5 rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-6 text-sm leading-7 text-soft">
          还没有生成结果。选好产品 / 平台 / 风格后点击「生成文案」。每次按当前风格生成一条；如果不满意可点单条卡片下方的「再生成一条」追加候选。
        </div>
      ) : (
        <div className="mt-5 space-y-5">
          {platform?.types.map((adType) => {
            const variants = grouped[adType.id] || [];
            return (
              <div key={adType.id} className="rounded-card border border-line bg-white px-4 py-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm font-semibold text-ink">
                    {adType.name_zh} · 上限 {adType.limit} 字符
                    {adType.internal_estimate ? " *" : ""}
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={busy !== "idle"}
                      onClick={() => onReplace(adType.id)}
                      className="rounded-pill border border-line bg-white px-3 py-1 text-xs font-semibold text-soft hover:text-ink disabled:opacity-60"
                    >
                      {busy === `replace:${adType.id}` ? "重新生成中…" : "重新生成"}
                    </button>
                    <button
                      type="button"
                      disabled={busy !== "idle"}
                      onClick={() => onAppend(adType.id)}
                      className="rounded-pill bg-ink px-3 py-1 text-xs font-semibold text-white disabled:opacity-60"
                    >
                      {busy === `append:${adType.id}` ? "生成中…" : "再生成一条"}
                    </button>
                  </div>
                </div>
                {variants.length === 0 ? (
                  <div className="mt-3 text-xs text-soft">本类型暂无候选，点上方按钮生成。</div>
                ) : (
                  <div className="mt-3 space-y-3">
                    {variants.map((item, idx) => (
                      <CopyCard key={`${adType.id}-${idx}`} item={item} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function CopyCard({ item }: { item: CopywriterGeneratedItem }) {
  const [copiedField, setCopiedField] = useState<"en" | "zh" | null>(null);
  const charOver = item.char_count > item.limit;

  async function handleCopy(text: string, field: "en" | "zh") {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 1500);
    } catch {
      // ignore
    }
  }

  return (
    <div className="rounded-card border border-line bg-[#fffafb] px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={[
              "rounded-pill px-3 py-1 font-semibold",
              charOver
                ? "bg-[#fff3f5] text-[#b44655]"
                : "bg-[#e8f8f0] text-[#3d8b74]",
            ].join(" ")}
          >
            {item.char_count}/{item.limit}
          </span>
          <span
            className={[
              "rounded-pill px-3 py-1 font-semibold",
              item.compliant
                ? "bg-[#e8f8f0] text-[#3d8b74]"
                : "bg-[#fff3f5] text-[#b44655]",
            ].join(" ")}
          >
            {item.compliant ? "✓ 合规" : "⚠ 风险"}
          </span>
          <span className="rounded-pill bg-white px-3 py-1 font-semibold text-soft">
            {item.style}
          </span>
        </div>
      </div>
      {!item.compliant && item.compliance_notes.length > 0 ? (
        <div className="mt-2 text-xs leading-5 text-[#b44655]">
          {item.compliance_notes.join("；")}
        </div>
      ) : null}
      <div className="mt-3 flex items-start justify-between gap-2">
        <p className="flex-1 whitespace-pre-line text-sm leading-7 text-ink">{item.en || "—"}</p>
        <button
          type="button"
          onClick={() => handleCopy(item.en, "en")}
          className="shrink-0 rounded-pill border border-line bg-white p-1.5 text-soft hover:text-ink"
          title="复制英文"
        >
          <ClipboardCopy className="h-3.5 w-3.5" />
        </button>
      </div>
      {copiedField === "en" ? (
        <div className="mt-1 text-[10px] text-[#3d8b74]">已复制英文</div>
      ) : null}
      <div className="mt-3 flex items-start justify-between gap-2">
        <p className="flex-1 text-xs leading-6 text-soft">中文参考：{item.zh || "—"}</p>
        {item.zh ? (
          <button
            type="button"
            onClick={() => handleCopy(item.zh, "zh")}
            className="shrink-0 rounded-pill border border-line bg-white p-1.5 text-soft hover:text-ink"
            title="复制中文"
          >
            <ClipboardCopy className="h-3.5 w-3.5" />
          </button>
        ) : null}
      </div>
      {copiedField === "zh" ? (
        <div className="mt-1 text-[10px] text-[#3d8b74]">已复制中文</div>
      ) : null}
    </div>
  );
}

function groupByType(items: CopywriterGeneratedItem[]): Record<string, CopywriterGeneratedItem[]> {
  return items.reduce<Record<string, CopywriterGeneratedItem[]>>((acc, item) => {
    (acc[item.type_id] = acc[item.type_id] || []).push(item);
    return acc;
  }, {});
}
