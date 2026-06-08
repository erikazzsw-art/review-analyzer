import type { ReactNode } from "react";

import { SiteHeader } from "@/components/marketing/site-header";

type MarketingShellProps = {
  eyebrow?: string;
  title: string;
  description: string;
  children?: ReactNode;
  aside?: ReactNode;
};

export function MarketingShell({
  eyebrow,
  title,
  description,
  children,
  aside,
}: MarketingShellProps) {
  return (
    <div className="min-h-screen bg-hero-wash">
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-6 pb-16 pt-4 lg:px-10">
        <section className="grid gap-6 lg:grid-cols-[minmax(0,1.02fr)_minmax(320px,0.98fr)] lg:items-stretch">
          <div className="rounded-shell border border-line bg-card px-7 py-8 shadow-card backdrop-blur md:px-10 md:py-10">
            {eyebrow ? (
              <div className="mb-5 inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold uppercase tracking-[0.12em] text-[#d94d72]">
                {eyebrow}
              </div>
            ) : null}
            <h1 className="max-w-3xl font-heading text-4xl font-extrabold leading-[1.02] tracking-[-0.04em] text-ink md:text-5xl">
              {title}
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-8 text-soft md:text-lg">
              {description}
            </p>
            {children ? <div className="mt-8">{children}</div> : null}
          </div>
          <div className="rounded-shell border border-line bg-white/78 p-6 shadow-card backdrop-blur md:p-8">
            {aside}
          </div>
        </section>
      </main>
    </div>
  );
}
