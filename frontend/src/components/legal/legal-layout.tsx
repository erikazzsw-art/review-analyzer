"use client";

import { useEffect, useState, useCallback, type ReactNode } from "react";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";

export type TocItem = {
  id: string;
  label: string;
};

type LegalLayoutProps = {
  tocItems: TocItem[];
  children: ReactNode;
};

export function LegalLayout({ tocItems, children }: LegalLayoutProps) {
  const [activeId, setActiveId] = useState<string>(tocItems[0]?.id ?? "");

  useEffect(() => {
    if (tocItems.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target?.id) {
          setActiveId(visible.target.id);
        }
      },
      {
        rootMargin: "-10% 0px -70% 0px",
        threshold: [0, 0.25, 0.5, 0.75, 1],
      },
    );

    const ids = new Set(tocItems.map((t) => t.id));
    // Observe every matching element – some may not exist yet (client-only
    // render), but we silently skip those.
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [tocItems]);

  const handleClick = useCallback(
    (id: string) => {
      const el = document.getElementById(id);
      if (!el) return;
      const y =
        el.getBoundingClientRect().top + window.scrollY - 100;
      window.scrollTo({ top: y, behavior: "smooth" });
      setActiveId(id);
    },
    [],
  );

  const hasToc = tocItems.length > 0;

  return (
    <div className="page-bg-warm relative min-h-screen overflow-hidden">
      {/* V3 floating blob decorations */}
      <div className="blob-rose absolute -left-32 -top-32 z-0" />
      <div className="blob-lavender absolute -right-24 top-20 z-0" />

      <SiteHeader />

      <main className="relative z-10 mx-auto w-full max-w-7xl px-6 pb-16 pt-4 lg:px-10">
        <div className="flex justify-center gap-10 lg:gap-12">
          {/* Main content — glass-white card, 680px max-width, 32px padding */}
          <div className="glass-white w-full max-w-[680px] shrink-0 p-8">
            {children}
          </div>

          {/* Sticky TOC sidebar — desktop only */}
          {hasToc && (
            <aside className="hidden w-52 shrink-0 lg:block">
              <nav className="sticky top-[104px]">
                <h4 className="mb-4 text-xs font-bold uppercase tracking-[0.1em] text-soft/50">
                  On this page
                </h4>
                <ul className="space-y-0.5 border-l border-line/60 pl-4">
                  {tocItems.map((item) => {
                    const isActive = activeId === item.id;
                    return (
                      <li key={item.id}>
                        <button
                          type="button"
                          onClick={() => handleClick(item.id)}
                          className={`group relative -ml-[17px] flex items-center gap-2.5 py-1.5 pl-[17px] text-left text-sm leading-snug transition-colors ${
                            isActive
                              ? "font-semibold text-ink"
                              : "text-soft hover:text-ink/70"
                          }`}
                        >
                          {/* Rose dot indicator */}
                          <span
                            className={`inline-block h-2 w-2 shrink-0 rounded-full transition-all ${
                              isActive
                                ? "scale-100 bg-rose shadow-[0_0_6px_rgba(243,111,143,0.5)]"
                                : "scale-75 bg-soft/25 group-hover:bg-soft/40"
                            }`}
                          />
                          {item.label}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </nav>
            </aside>
          )}
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
