"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Menu, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { LocaleSwitcher } from "@/components/ui/locale-switcher";

export function SiteHeader() {
  const t = useTranslations("header");
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  const navItems = [
    { href: "/features", label: t("features") },
    { href: "/pricing", label: t("pricing") },
    { href: "/blog", label: t("blog") },
    { href: "/login", label: t("login") },
  ];

  return (
    <header
      className={`sticky top-0 z-50 h-[72px] transition-all duration-300 ${
        scrolled
          ? "glass-white rounded-none border-b border-[rgba(0,0,0,0.06)] shadow-sm"
          : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex h-full w-full max-w-7xl items-center justify-between px-6 lg:px-10">
        {/* Logo */}
        <Link
          href="/"
          className="inline-flex items-center gap-2.5"
          onClick={closeMobile}
        >
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-xs font-extrabold text-white shadow-sm">
            RL
          </span>
          <span className="font-heading text-lg font-extrabold tracking-[-0.02em] text-ink">
            ReviewLens
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-1 md:flex">
          <LocaleSwitcher variant="header" />
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="group relative rounded-pill px-3 py-2 text-sm font-semibold text-soft transition-colors hover:text-ink"
            >
              {item.label}
              <span className="absolute bottom-1 left-1/2 h-[2px] w-0 -translate-x-1/2 rounded-full bg-[#f36f8f] transition-all duration-300 group-hover:w-[60%]" />
            </Link>
          ))}
          <Button
            href="/register"
            variant="marketing"
            size="marketing"
            className="ml-2"
          >
            {t("register")}
          </Button>
        </nav>

        {/* Mobile hamburger */}
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-lg p-2 text-ink md:hidden"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
        >
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <div className="glass-white mx-4 mt-2 rounded-[20px] p-4 shadow-glass md:hidden">
          <nav className="flex flex-col gap-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-xl px-4 py-3 text-sm font-semibold text-soft transition-colors hover:bg-[rgba(243,111,143,0.06)] hover:text-ink"
                onClick={closeMobile}
              >
                {item.label}
              </Link>
            ))}
            <hr className="my-2 border-[rgba(0,0,0,0.06)]" />
            <Button
              href="/register"
              variant="marketing"
              size="marketing"
              className="w-full justify-center"
              onClick={closeMobile}
            >
              {t("register")}
            </Button>
            <div className="mt-2 flex justify-center">
              <LocaleSwitcher variant="header" />
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
