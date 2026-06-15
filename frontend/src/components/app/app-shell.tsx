import Link from "next/link";
import type { ReactNode } from "react";

import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";

type AppShellProps = {
  currentPath:
    | "/workspace"
    | "/products"
    | "/upload"
    | "/qa"
    | "/actions"
    | "/reviews"
    | "/copywriter"
    | "/settings"
    | "/analysis/results"
    | "/analysis/compare"
    | "/analysis/history";
  title: string;
  description: string;
  children: ReactNode;
};

const navItems = [
  { href: "/workspace", label: "今日工作台" },
  { href: "/products", label: "产品管理" },
  { href: "/upload", label: "上传评论" },
  { href: "/analysis/results", label: "分析结果" },
  { href: "/analysis/compare", label: "对比分析" },
  { href: "/analysis/history", label: "历史记录" },
  { href: "/qa", label: "问评论" },
  { href: "/actions", label: "行动中心" },
  { href: "/reviews", label: "复盘追踪" },
  { href: "/copywriter", label: "宣传文案" },
  { href: "/settings", label: "推送设置" },
];

export function AppShell({
  currentPath,
  title,
  description,
  children,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-hero-wash">
      <header className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-6 py-6 lg:px-10">
        <div className="flex flex-col gap-4 rounded-shell border border-line bg-white/72 px-5 py-5 shadow-card backdrop-blur md:flex-row md:items-center md:justify-between md:px-7">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="inline-flex h-12 w-12 items-center justify-center rounded-[18px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-base font-extrabold text-white shadow-glow"
            >
              CA
            </Link>
            <div>
              <div className="font-heading text-xl font-extrabold tracking-[-0.03em] text-ink">
                ClueAI
              </div>
              <div className="text-sm text-soft">
                SKU 口碑改版追踪系统
              </div>
            </div>
          </div>

          <nav className="flex flex-wrap gap-2">
            {navItems.map((item) => {
              const isActive = item.href === currentPath;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={[
                    "inline-flex min-h-11 items-center justify-center rounded-pill border px-4 py-2 text-sm font-semibold transition",
                    isActive
                      ? "border-transparent bg-ink text-white shadow-card"
                      : "border-line bg-white/82 text-soft hover:bg-white hover:text-ink",
                  ].join(" ")}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <section className="rounded-shell border border-line bg-card px-6 py-8 shadow-card backdrop-blur md:px-8">
          <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
            NEXT.JS APP PREVIEW
          </div>
          <h1 className="mt-5 max-w-4xl font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink md:text-[3.2rem]">
            {title}
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-8 text-soft md:text-lg">
            {description}
          </p>
        </section>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 pb-16 lg:px-10">
        {children}
      </main>

      <FeedbackWidget />
    </div>
  );
}
