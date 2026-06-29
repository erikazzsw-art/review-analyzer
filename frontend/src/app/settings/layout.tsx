"use client";

import { usePathname } from "next/navigation";

import { Sidebar } from "@/components/app/sidebar";
import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-hero-wash">
      <Sidebar currentPath={pathname} />

      <div className="pt-14 md:pl-[260px] md:pt-0">
        {children}
      </div>

      <FeedbackWidget />
    </div>
  );
}
