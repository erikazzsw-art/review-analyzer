"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Menu,
  X,
  User,
} from "lucide-react";

type SidebarProps = {
  currentPath: string;
  userName?: string;
  planLabel?: string;
};

const navGroups = [
  {
    title: "核心",
    items: [
      { href: "/workspace", label: "工作台" },
      { href: "/upload", label: "上传评论" },
      { href: "/analysis/results", label: "分析结果" },
    ],
  },
  {
    title: "洞察",
    items: [
      { href: "/analysis/compare", label: "对比分析" },
      { href: "/analysis/history", label: "历史记录" },
      { href: "/qa", label: "问评论" },
    ],
  },
  {
    title: "行动",
    items: [
      { href: "/actions", label: "行动中心" },
      { href: "/reviews", label: "复盘追踪" },
      { href: "/copywriter", label: "宣传文案" },
    ],
  },
  {
    title: "管理",
    items: [
      { href: "/products", label: "产品管理" },
      { href: "/settings", label: "推送设置" },
      { href: "/settings/observability", label: "可观测性" },
    ],
  },
];

export function Sidebar({ currentPath, userName, planLabel }: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const navContent = (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-6">
        <Link
          href="/"
          className="inline-flex h-10 w-10 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-sm font-extrabold text-white shadow-glow"
        >
          CA
        </Link>
        <div>
          <div className="font-heading text-base font-extrabold tracking-[-0.03em] text-ink">
            ClueAI
          </div>
          <div className="text-xs text-soft">评论智能分析</div>
        </div>
      </div>

      {/* Nav groups */}
      <nav className="flex-1 overflow-y-auto px-3 py-2">
        {navGroups.map((group) => (
          <div key={group.title} className="mb-5">
            <div className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-soft/70">
              {group.title}
            </div>
            {group.items.map((item) => {
              const isActive = item.href === currentPath;
              return (
                <a
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  className={[
                    "relative mb-0.5 flex w-full items-center justify-start gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-roseSoft text-ink hover:bg-roseSoft"
                      : "text-soft hover:bg-white/60 hover:text-ink",
                  ].join(" ")}
                >
                  {isActive && (
                    <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-rose" />
                  )}
                  {item.label}
                </a>
              );
            })}
          </div>
        ))}
      </nav>

      {/* User info */}
      <div className="px-4 py-4">
        <div className="mb-4 h-px bg-line" />
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-lavender/10 text-lavender">
            <User size={16} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-ink">
              {userName || "未登录"}
            </div>
            {planLabel && (
              <div className="text-xs text-soft">{planLabel}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="fixed left-0 top-0 hidden h-screen w-[260px] border-r border-line bg-white md:block">
        {navContent}
      </aside>

      {/* Mobile top bar */}
      <div className="fixed left-0 right-0 top-0 z-40 flex h-14 items-center justify-between border-b border-line bg-white/95 px-4 backdrop-blur md:hidden">
        <div className="flex items-center gap-2">
          <a
            href="/"
            className="inline-flex h-8 w-8 items-center justify-center rounded-[10px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-xs font-extrabold text-white"
          >
            CA
          </a>
          <span className="font-heading text-sm font-bold text-ink">ClueAI</span>
        </div>
        <button
          type="button"
          onClick={() => setMobileOpen((prev) => !prev)}
          aria-label={mobileOpen ? "关闭菜单" : "打开菜单"}
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-line bg-white text-ink hover:bg-roseSoft"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-ink/30 backdrop-blur-sm md:hidden"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="fixed left-0 top-0 z-50 h-screen w-[280px] bg-white shadow-glow md:hidden">
            {navContent}
          </aside>
        </>
      )}
    </>
  );
}
