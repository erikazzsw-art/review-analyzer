"use client";

import { RefreshCw } from "lucide-react";

import type { CopywriterIdealProfile } from "@/lib/api/types";

type Props = {
  profile: CopywriterIdealProfile | null;
  loading: boolean;
  onRegenerate?: () => void;
};

export function IdealProfileCard({ profile, loading, onRegenerate }: Props) {
  return (
    <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            INSIGHT
          </div>
          <h3 className="mt-4 font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            理想产品画像
          </h3>
        </div>
        {onRegenerate ? (
          <button
            type="button"
            onClick={onRegenerate}
            disabled={loading}
            className="inline-flex items-center gap-1 rounded-pill border border-line bg-white px-3 py-1.5 text-xs font-semibold text-soft hover:text-ink disabled:opacity-60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            {loading ? "重新生成中…" : "重新生成"}
          </button>
        ) : null}
      </div>

      {profile ? (
        <>
          <div className="mt-4 text-xs leading-6 text-soft">
            {profile.cached ? "命中缓存" : "本次新生成"} ·{" "}
            基于 {profile.comment_count_at_generation} 条评论
            {profile.generated_at
              ? ` · ${new Date(profile.generated_at).toLocaleString("zh-CN")}`
              : ""}
          </div>
          {profile.features.length > 0 ? (
            <div className="mt-4">
              <div className="text-xs font-semibold uppercase tracking-[0.08em] text-soft">
                关键特性
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {profile.features.map((feature) => (
                  <span
                    key={feature}
                    className="rounded-pill bg-[#fff1f5] px-3 py-1 text-xs font-semibold text-[#d94d72]"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
          <ProfileRow label="价格预期" value={profile.price_range} />
          <ProfileRow label="物流时效" value={profile.logistics} />
          <ProfileRow label="包装期望" value={profile.packaging} />
          <ProfileRow label="售后要求" value={profile.service} />
          {profile.summary ? (
            <p className="mt-5 whitespace-pre-line rounded-card border border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-ink">
              {profile.summary}
            </p>
          ) : null}
        </>
      ) : (
        <p className="mt-5 text-sm leading-7 text-soft">
          生成文案时会自动构建该产品的理想客户画像。相同产品 + 版本 + 评论范围下，第二次会直接命中缓存。
        </p>
      )}
    </section>
  );
}

function ProfileRow({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div className="mt-3 text-sm leading-6">
      <span className="text-xs font-semibold uppercase tracking-[0.08em] text-soft">{label}</span>
      <div className="mt-1 text-ink">{value}</div>
    </div>
  );
}
