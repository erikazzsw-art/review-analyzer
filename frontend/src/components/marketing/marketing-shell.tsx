import type { ReactNode } from "react";

import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";

type MarketingShellProps = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  description: string;
  children?: ReactNode;
  aside?: ReactNode;
  cta?: ReactNode;
};

export function MarketingShell({
  eyebrow,
  title,
  subtitle,
  description,
  children,
  aside,
  cta,
}: MarketingShellProps) {
  return (
    <div className="min-h-screen bg-hero-wash">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-6 pb-16 pt-4 lg:px-10">
        <section className="rounded-shell border border-line bg-card px-7 py-8 shadow-card backdrop-blur md:px-10 md:py-10">
          {/* Top row: title area + CTA */}
          <div className="flex items-start justify-between gap-6">
            <div className="max-w-2xl">
              {eyebrow ? (
                <div className="mb-4 inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold uppercase tracking-[0.12em] text-[#d94d72]">
                  {eyebrow}
                </div>
              ) : null}
              <h1 className="font-heading text-4xl font-extrabold leading-[1.02] tracking-[-0.04em] text-ink md:text-5xl">
                {title}
              </h1>
              {subtitle ? (
                <p className="mt-3 font-heading text-xl font-bold tracking-[-0.02em] text-ink/80">
                  {subtitle}
                </p>
              ) : null}
              <p className="mt-4 text-base leading-8 text-soft md:text-lg">
                {description}
              </p>
            </div>
            {cta ? <div className="hidden shrink-0 md:block">{cta}</div> : null}
          </div>

          {/* Data cards grid */}
          {aside ? <div className="mt-8">{aside}</div> : null}

          {/* Mobile CTA + children */}
          <div className="mt-6 flex flex-col gap-3 md:hidden">
            {cta}
          </div>
          {children ? <div className="mt-8">{children}</div> : null}
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
