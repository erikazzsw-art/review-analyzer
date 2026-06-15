import type { ReactNode } from "react";

import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";
import { Sidebar } from "@/components/app/sidebar";

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

export function AppShell({
  currentPath,
  title,
  description,
  children,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-hero-wash">
      <Sidebar currentPath={currentPath} />

      {/* Main content area */}
      <div className="pt-14 md:pl-[260px] md:pt-0">
        <header className="px-6 pb-2 pt-8 lg:px-10">
          <h1 className="font-heading text-2xl font-extrabold tracking-[-0.03em] text-ink md:text-3xl">
            {title}
          </h1>
          <p className="mt-1.5 text-sm leading-6 text-soft md:text-base">
            {description}
          </p>
        </header>

        <main className="flex flex-col gap-6 px-6 pb-20 pt-4 lg:gap-8 lg:px-10">
          {children}
        </main>
      </div>

      <FeedbackWidget />
    </div>
  );
}
