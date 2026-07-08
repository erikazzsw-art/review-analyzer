"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import {
  Menu,
  X,
} from "lucide-react";
import { useTranslations } from "next-intl";

import { LocaleSwitcher } from "@/components/ui/locale-switcher";
import { FeedbackTrigger } from "@/components/feedback/FeedbackWidget";
import { SidebarCreditEntry } from "@/components/credit/sidebar-credit-entry";
import { SidebarUserMenu } from "@/components/app/sidebar-user-menu";

type MeData = { username: string; plan: string; is_admin: boolean };

function useMe(): MeData | null {
  const [me, setMe] = useState<MeData | null>(null);
  useEffect(() => {
    fetch("/api/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setMe(d as MeData); })
      .catch(() => {});
  }, []);
  return me;
}

type SidebarProps = {
  currentPath: string;
};

export function Sidebar({ currentPath }: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const t = useTranslations("sidebar");
  const me = useMe();

  const isAdmin = me?.is_admin ?? false;

  const navGroups = [
    {
      title: t("groupCore"),
      items: [
        { href: "/workspace", label: t("workspace") },
        { href: "/upload", label: t("upload") },
        { href: "/analysis/results", label: t("analysisResults") },
      ],
    },
    {
      title: t("groupInsight"),
      items: [
        { href: "/analysis/compare", label: t("compare") },
        { href: "/analysis/history", label: t("history") },
        { href: "/qa", label: t("askReviews") },
      ],
    },
    {
      title: t("groupAction"),
      items: [
        { href: "/actions", label: t("actionCenter") },
        { href: "/reviews", label: t("reviewTracking") },
        { href: "/copywriter", label: t("copywriter") },
      ],
    },
    {
      title: t("groupManage"),
      items: [
        { href: "/products", label: t("products") },
        { href: "/settings/account", label: t("accountSettings") },
        { href: "/settings/golden-set", label: t("goldenSet"), adminOnly: true },
        { href: "/settings/push", label: t("pushSettings") },
        { href: "/settings/observability", label: t("observability"), adminOnly: true },
      ],
    },
  ].map((group) => ({
    ...group,
    items: group.items.filter((item) => !("adminOnly" in item && item.adminOnly) || isAdmin),
  }));

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
          <div className="text-xs text-soft">{t("tagline")}</div>
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
        <SidebarCreditEntry />
        <div className="mb-3 flex items-center gap-1">
          <LocaleSwitcher variant="sidebar" />
          <FeedbackTrigger />
        </div>
        <div className="mb-3 h-px bg-line" />
        <SidebarUserMenu username={me?.username ?? null} plan={me?.plan ?? null} />
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
          aria-label={mobileOpen ? t("closeMenu") : t("openMenu")}
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
