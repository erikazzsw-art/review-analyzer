"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { initAnalytics, trackPageView } from "@/lib/analytics";

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  let pathname = "/";
  try {
    pathname = usePathname();
  } catch {
    pathname = "/";
  }

  useEffect(() => {
    try {
      initAnalytics();
    } catch {
      // Analytics should never block rendering.
    }
  }, []);

  useEffect(() => {
    try {
      trackPageView(pathname);
    } catch {
      // Ignore analytics failures.
    }
  }, [pathname]);

  return <>{children}</>;
}
