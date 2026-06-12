import posthog from "posthog-js";

let initialized = false;

export function initAnalytics() {
  if (initialized || typeof window === "undefined") return;

  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  const host =
    process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://app.posthog.com";

  if (!key) return;

  posthog.init(key, {
    api_host: host,
    autocapture: true,
    capture_pageview: false,
    capture_pageleave: true,
    persistence: "localStorage",
    ip: false,
    respect_dnt: true,
    secure_cookie: true,
  });
  initialized = true;
}

export function track(event: string, properties?: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  posthog.capture(event, {
    ...properties,
    page_path: window.location.pathname,
  });
}

export function identify(userId: string, traits: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  posthog.identify(userId, traits);
}

export function reset() {
  if (typeof window === "undefined") return;
  posthog.reset();
}

export function trackPageView(path: string) {
  if (typeof window === "undefined") return;
  posthog.capture("$pageview", { $current_url: path });
}
