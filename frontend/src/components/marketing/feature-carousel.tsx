"use client";

import {
  BarChart3,
  ChevronLeft,
  ChevronRight,
  FileSearch,
  GitCompare,
  History,
  MessageCircle,
  Target,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

/* ------------------------------------------------------------------ */
/*  Data                                                               */
/* ------------------------------------------------------------------ */

const TAB_KEYS = [
  "dashboard",
  "ask",
  "analysis",
  "action",
  "compare",
  "review",
] as const;

type TabKey = (typeof TAB_KEYS)[number];

const TAB_ICONS: Record<TabKey, React.ComponentType<{ className?: string }>> = {
  dashboard: BarChart3,
  ask: MessageCircle,
  analysis: FileSearch,
  action: Target,
  compare: GitCompare,
  review: History,
};

/* ------------------------------------------------------------------ */
/*  Browser window chrome (CSS-only)                                    */
/* ------------------------------------------------------------------ */

function BrowserFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-[16px] border border-line bg-white shadow-[0_8px_40px_rgba(96,63,88,0.12)]">
      {/* Title bar */}
      <div className="flex items-center gap-2.5 border-b border-line bg-[#faf8f7] px-4 py-2.5">
        {/* Traffic lights */}
        <span className="inline-block h-3 w-3 rounded-full bg-[#ec6a5e]" />
        <span className="inline-block h-3 w-3 rounded-full bg-[#f5bf4f]" />
        <span className="inline-block h-3 w-3 rounded-full bg-[#61c454]" />
        {/* Address bar */}
        <div className="ml-3 flex-1 rounded-full bg-white px-3 py-1 text-[11px] text-soft border border-line/60">
          app.clueai-reviewlens.com/
          <span className="text-ink/50">analytics</span>
        </div>
      </div>
      {/* Content slot */}
      <div className="relative bg-[#fdfbfb]">{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Individual mockup screens                                           */
/* ------------------------------------------------------------------ */

function DashboardMockup() {
  const stats = [
    { label: "总评论", value: "661", color: "text-ink" },
    { label: "好评率", value: "57.9%", color: "text-mint" },
    { label: "差评率", value: "42.1%", color: "text-rose" },
    { label: "评分", value: "3.5 / 5", color: "text-amber" },
  ];
  const bars = [78, 65, 52, 48, 41, 35, 28];
  const days = ["07-14", "07-15", "07-16", "07-17", "07-18", "07-19", "07-20"];

  return (
    <div className="space-y-5 p-6">
      {/* Stat cards row */}
      <div className="grid grid-cols-4 gap-3">
        {stats.map((s) => (
          <div
            key={s.label}
            className="rounded-xl border border-line/80 bg-white px-4 py-3 shadow-[0_2px_8px_rgba(0,0,0,0.03)]"
          >
            <div className="font-body text-[11px] text-soft">{s.label}</div>
            <div className={`mt-1 font-heading text-xl font-bold ${s.color}`}>
              {s.value}
            </div>
          </div>
        ))}
      </div>

      {/* Bar chart */}
      <div className="rounded-xl border border-line/80 bg-white p-4">
        <div className="mb-3 font-body text-[11px] font-semibold text-soft uppercase tracking-wider">
          7 天差评趋势
        </div>
        <div className="flex items-end justify-between gap-2 h-[100px]">
          {bars.map((h, i) => (
            <div key={i} className="flex flex-1 flex-col items-center gap-1.5">
              <div
                className="w-full max-w-[32px] rounded-t-md bg-rose/70"
                style={{ height: `${h}%` }}
              />
              <span className="font-body text-[10px] text-soft/70">
                {days[i]}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-1.5 font-body text-[11px] text-mint">
          <span className="inline-block h-2 w-2 rounded-full bg-mint" />
          差评率持续下降 ↓32%
        </div>
      </div>
    </div>
  );
}

function AskMockup() {
  return (
    <div className="space-y-4 p-6">
      {/* User message */}
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-br-md bg-roseSoft px-4 py-2.5 font-body text-[13px] text-ink shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
          拉链质量问题有多少条？
        </div>
      </div>
      {/* AI response */}
      <div className="flex justify-start">
        <div className="max-w-[82%] space-y-3 rounded-2xl rounded-bl-md border border-line bg-white px-4 py-3 shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
          <p className="font-body text-[13px] leading-relaxed text-ink">
            共 <span className="font-bold text-rose">47 条</span>{" "}
            差评提到拉链问题，占比{" "}
            <span className="font-bold text-rose">32%</span>
            ，主要集中在 2026 年 5-6 月。
          </p>
          <div className="flex gap-3">
            {[
              { v: "47", l: "条差评" },
              { v: "32%", l: "占比" },
              { v: "↓", l: "趋势" },
            ].map((s) => (
              <div
                key={s.l}
                className="flex-1 rounded-lg bg-roseSoft/50 px-2.5 py-1.5 text-center"
              >
                <div className="font-heading text-sm font-bold text-rose">
                  {s.v}
                </div>
                <div className="font-body text-[10px] text-soft">{s.l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      {/* Typing indicator */}
      <div className="flex items-center gap-1.5 px-1">
        <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-soft/40 [animation-delay:0ms]" />
        <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-soft/40 [animation-delay:150ms]" />
        <span className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-soft/40 [animation-delay:300ms]" />
      </div>
    </div>
  );
}

function AnalysisMockup() {
  const rows = [
    {
      name: "张***",
      stars: 4,
      snippet: "拉链很顺滑，做工比预期好很多",
      sentiment: "正面",
      sentimentColor: "bg-mint/10 text-mint border-mint/30",
      tags: ["易用性", "耐用性"],
    },
    {
      name: "李***",
      stars: 2,
      snippet: "用了两周拉链就卡住了，很失望",
      sentiment: "负面",
      sentimentColor: "bg-rose/10 text-rose border-rose/30",
      tags: ["做工质量"],
    },
    {
      name: "王***",
      stars: 3,
      snippet: "性价比不错，就是包装有点简陋",
      sentiment: "中性",
      sentimentColor: "bg-amber/10 text-amber border-amber/30",
      tags: ["性价比", "包装"],
    },
  ];

  return (
    <div className="p-5">
      <div className="overflow-hidden rounded-xl border border-line/80 bg-white">
        {/* Table header */}
        <div className="grid grid-cols-[1fr_60px_2fr_56px_1fr] gap-2 border-b border-line bg-[#faf8f7] px-4 py-2 font-body text-[10px] font-semibold text-soft uppercase tracking-wider">
          <span>评论者</span>
          <span>评分</span>
          <span>内容摘要</span>
          <span>情感</span>
          <span>主题标签</span>
        </div>
        {/* Rows */}
        {rows.map((r, i) => (
          <div
            key={i}
            className="grid grid-cols-[1fr_60px_2fr_56px_1fr] gap-2 border-b border-line/40 px-4 py-2.5 last:border-0 items-center"
          >
            <span className="font-body text-[12px] text-ink">{r.name}</span>
            <span className="font-body text-[12px] text-amber">
              {"★".repeat(r.stars)}
              {"☆".repeat(5 - r.stars)}
            </span>
            <span className="truncate font-body text-[12px] text-ink/80">
              {r.snippet}
            </span>
            <span
              className={`inline-block rounded-full border px-2 py-0.5 text-center font-body text-[10px] ${r.sentimentColor}`}
            >
              {r.sentiment}
            </span>
            <span className="flex gap-1 flex-wrap">
              {r.tags.map((t) => (
                <span
                  key={t}
                  className="rounded-full bg-lavender/10 px-2 py-0.5 font-body text-[10px] text-lavender"
                >
                  {t}
                </span>
              ))}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ActionMockup() {
  const columns = [
    {
      title: "待处理",
      color: "border-l-amber",
      count: 2,
      cards: [
        { title: "拉链卡顿问题", product: "户外背包 A-300", priority: "bg-rose" },
        { title: "肩带脱线反馈", product: "户外背包 A-300", priority: "bg-amber" },
      ],
    },
    {
      title: "进行中",
      color: "border-l-lavender",
      count: 1,
      cards: [
        {
          title: "改进拉链供应商",
          product: "户外背包 A-300",
          priority: "bg-amber",
        },
      ],
    },
    {
      title: "已完成",
      color: "border-l-mint",
      count: 4,
      cards: [
        { title: "更换包装材料", product: "户外背包 A-300", priority: "bg-mint" },
        { title: "增加内衬加固", product: "腰包 B-100", priority: "bg-mint" },
        { title: "升级拉链品牌", product: "腰包 B-100", priority: "bg-mint" },
      ],
    },
  ];

  return (
    <div className="grid grid-cols-3 gap-3 p-5">
      {columns.map((col) => (
        <div key={col.title}>
          <div className="mb-2 flex items-center gap-1.5 font-body text-[11px] font-semibold text-soft">
            <span className="inline-block h-2 w-2 rounded-full bg-soft/50" />
            {col.title}
            <span className="ml-auto text-[10px] text-soft/60">{col.count}</span>
          </div>
          <div className="space-y-2">
            {col.cards.map((card) => (
              <div
                key={card.title}
                className={`rounded-lg border border-line/80 ${col.color} border-l-[3px] bg-white px-3 py-2.5 shadow-[0_1px_4px_rgba(0,0,0,0.03)]`}
              >
                <div className="flex items-center gap-1.5">
                  <span className={`inline-block h-1.5 w-1.5 rounded-full ${card.priority}`} />
                  <span className="font-body text-[12px] font-semibold text-ink">
                    {card.title}
                  </span>
                </div>
                <div className="mt-1 font-body text-[10px] text-soft/70">
                  {card.product}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function CompareMockup() {
  return (
    <div className="grid grid-cols-2 divide-x divide-line/60 p-5">
      {/* Before */}
      <div className="pr-4">
        <div className="mb-3 inline-block rounded-full bg-rose/10 px-2.5 py-0.5 font-body text-[10px] font-semibold text-rose">
          导入前
        </div>
        <div className="space-y-1.5 rounded-lg border border-line/60 bg-[#fdfbfb] p-3">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="flex gap-2 font-body text-[10px] text-soft/60"
            >
              <span className="w-5 shrink-0 text-right">{i + 1}</span>
              <span className="truncate">
                {[
                  "拉链,卡顿,质量问题,差评...",
                  "尺寸偏小,退货,不满意...",
                  "颜色色差,与图片不符...",
                  "面料起球,洗涤后缩水...",
                  "包装破损,物流慢,差评...",
                ][i]}
              </span>
            </div>
          ))}
        </div>
      </div>
      {/* After */}
      <div className="pl-4">
        <div className="mb-3 inline-block rounded-full bg-mint/10 px-2.5 py-0.5 font-body text-[10px] font-semibold text-mint">
          分析后
        </div>
        <div className="space-y-3 rounded-lg border border-line/60 bg-white p-3">
          <div className="flex items-center gap-3">
            <div className="flex-1 rounded-lg bg-mint/5 px-3 py-2 text-center">
              <div className="font-heading text-lg font-bold text-mint">
                ↓62%
              </div>
              <div className="font-body text-[10px] text-soft">差评率下降</div>
            </div>
            <div className="flex-1 rounded-lg bg-lavender/5 px-3 py-2 text-center">
              <div className="font-heading text-lg font-bold text-lavender">
                47
              </div>
              <div className="font-body text-[10px] text-soft">改进项</div>
            </div>
          </div>
          <div className="rounded-lg border border-mint/30 bg-mint/5 px-3 py-2">
            <div className="font-body text-[10px] font-semibold text-mint">
              💡 改版建议
            </div>
            <div className="mt-1 font-body text-[11px] text-ink/80">
              优先处理拉链问题（32% 差评），建议更换 YKK 供应商
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReviewTimelineMockup() {
  const events = [
    {
      date: "2026-07-15",
      text: "拉链升级方案已执行，待验证效果",
      dot: "bg-mint",
    },
    {
      date: "2026-07-10",
      text: "产品会议确认：改用 YKK #5 金属拉链",
      dot: "bg-lavender",
    },
    {
      date: "2026-07-03",
      text: "AI 识别到拉链差评激增 47 条，自动创建追踪任务",
      dot: "bg-rose",
    },
  ];

  return (
    <div className="p-6">
      <div className="relative pl-8">
        {/* Vertical line */}
        <div className="absolute left-[11px] top-1 bottom-1 w-[2px] bg-rose/30" />
        <div className="space-y-6">
          {events.map((ev, i) => (
            <div key={i} className="relative">
              {/* Dot */}
              <span
                className={`absolute -left-[21px] top-1.5 inline-block h-2.5 w-2.5 rounded-full ${ev.dot} ring-2 ring-white`}
              />
              <span className="font-body text-[11px] text-soft/60">
                {ev.date}
              </span>
              <div className="mt-1 rounded-lg border border-line/80 bg-white px-3.5 py-2.5 shadow-[0_1px_4px_rgba(0,0,0,0.03)]">
                <p className="font-body text-[12px] leading-relaxed text-ink">
                  {ev.text}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const MOCKUPS: Record<TabKey, React.ComponentType> = {
  dashboard: DashboardMockup,
  ask: AskMockup,
  analysis: AnalysisMockup,
  action: ActionMockup,
  compare: CompareMockup,
  review: ReviewTimelineMockup,
};

/* ------------------------------------------------------------------ */
/*  FeatureCarousel                                                     */
/* ------------------------------------------------------------------ */

export function FeatureCarousel() {
  const t = useTranslations("features");
  const [activeIndex, setActiveIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const resumeRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimers = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (resumeRef.current) {
      clearTimeout(resumeRef.current);
      resumeRef.current = null;
    }
  }, []);

  const startAutoPlay = useCallback(() => {
    clearTimers();
    intervalRef.current = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % TAB_KEYS.length);
    }, 5000);
  }, [clearTimers]);

  const stopAutoPlay = useCallback(() => {
    clearTimers();
  }, [clearTimers]);

  const scheduleResume = useCallback(() => {
    clearTimers();
    resumeRef.current = setTimeout(() => {
      startAutoPlay();
    }, 3000);
  }, [clearTimers, startAutoPlay]);

  /* Bootstrap auto-play */
  useEffect(() => {
    startAutoPlay();
    return clearTimers;
  }, [startAutoPlay, clearTimers]);

  /* Hover handlers */
  const handleMouseEnter = useCallback(() => {
    setIsHovered(true);
    stopAutoPlay();
  }, [stopAutoPlay]);

  const handleMouseLeave = useCallback(() => {
    setIsHovered(false);
    scheduleResume();
  }, [scheduleResume]);

  const handleTabClick = useCallback(
    (idx: number) => {
      setActiveIndex(idx);
      // Manual click: pause then resume after 3s
      stopAutoPlay();
      scheduleResume();
    },
    [stopAutoPlay, scheduleResume],
  );

  const goPrev = useCallback(() => {
    setActiveIndex((prev) => (prev - 1 + TAB_KEYS.length) % TAB_KEYS.length);
    stopAutoPlay();
    scheduleResume();
  }, [stopAutoPlay, scheduleResume]);

  const goNext = useCallback(() => {
    setActiveIndex((prev) => (prev + 1) % TAB_KEYS.length);
    stopAutoPlay();
    scheduleResume();
  }, [stopAutoPlay, scheduleResume]);

  const ActiveMockup = MOCKUPS[TAB_KEYS[activeIndex]];

  return (
    <section
      className="relative mx-auto max-w-[960px]"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* ── PART 1: Tab bar ── */}
      <div className="mb-8 flex flex-wrap justify-center gap-2">
        {TAB_KEYS.map((key, idx) => {
          const Icon = TAB_ICONS[key];
          const isActive = idx === activeIndex;
          return (
            <button
              key={key}
              type="button"
              onClick={() => handleTabClick(idx)}
              className={`inline-flex items-center gap-1.5 rounded-full px-4 py-2 font-body text-[13px] font-medium transition-all duration-300 ${
                isActive
                  ? "bg-rose text-white shadow-[0_4px_16px_rgba(243,111,143,0.35)]"
                  : "bg-glass-white text-ink hover:bg-white/80"
              }`}
            >
              <Icon className="h-[14px] w-[14px]" />
              <span>{t(`tabs.${key}.name`)}</span>
            </button>
          );
        })}
      </div>

      {/* ── PART 2: Screenshot area ── */}
      <div className="relative">
        {/* Arrow buttons (visible on hover) */}
        <button
          type="button"
          onClick={goPrev}
          className={`absolute -left-5 top-1/2 z-10 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full border border-line/80 bg-white/80 backdrop-blur text-rose shadow-[0_2px_8px_rgba(0,0,0,0.06)] transition-all duration-300 hover:bg-white hover:shadow-[0_4px_16px_rgba(0,0,0,0.1)] ${
            isHovered ? "opacity-100" : "opacity-0"
          }`}
          aria-label="Previous"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>

        <button
          type="button"
          onClick={goNext}
          className={`absolute -right-5 top-1/2 z-10 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full border border-line/80 bg-white/80 backdrop-blur text-rose shadow-[0_2px_8px_rgba(0,0,0,0.06)] transition-all duration-300 hover:bg-white hover:shadow-[0_4px_16px_rgba(0,0,0,0.1)] ${
            isHovered ? "opacity-100" : "opacity-0"
          }`}
          aria-label="Next"
        >
          <ChevronRight className="h-5 w-5" />
        </button>

        {/* Screenshot */}
        <div className="relative transition-opacity duration-300 ease-in-out">
          <BrowserFrame>
            <div className="min-h-[360px]" key={TAB_KEYS[activeIndex]}>
              <ActiveMockup />
            </div>
          </BrowserFrame>
        </div>
      </div>

      {/* ── PART 3: Info bar ── */}
      <div className="mt-6 text-center">
        <div className="inline-flex items-center gap-2">
          {(() => {
            const Icon = TAB_ICONS[TAB_KEYS[activeIndex]];
            return <Icon className="h-5 w-5 text-rose" />;
          })()}
          <h3 className="font-heading text-xl font-extrabold text-ink">
            {t(`tabs.${TAB_KEYS[activeIndex]}.title`)}
          </h3>
        </div>
        <p className="mt-1 font-body text-[15px] text-soft">
          {t(`tabs.${TAB_KEYS[activeIndex]}.desc`)}
        </p>
      </div>

      {/* ── Dot indicators ── */}
      <div className="mt-6 flex items-center justify-center gap-1">
        {TAB_KEYS.map((_, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleTabClick(idx)}
            aria-label={`Go to tab ${idx + 1}`}
            className={`rounded-full transition-all duration-300 ${
              idx === activeIndex
                ? "h-2.5 w-2.5 bg-rose"
                : "h-1.5 w-1.5 bg-soft/30 hover:bg-soft/50"
            }`}
          />
        ))}
      </div>
    </section>
  );
}
