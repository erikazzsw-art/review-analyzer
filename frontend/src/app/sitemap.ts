import type { MetadataRoute } from "next";

import { absoluteUrl } from "@/lib/seo";

const marketingRoutes = [
  { path: "/", priority: 1, changeFrequency: "weekly" as const },
  { path: "/features", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/pricing", priority: 0.9, changeFrequency: "monthly" as const },
  { path: "/case-studies", priority: 0.8, changeFrequency: "monthly" as const },
  { path: "/trial", priority: 0.8, changeFrequency: "monthly" as const },
  { path: "/blog", priority: 0.8, changeFrequency: "weekly" as const },
];

const blogRoutes = [
  { path: "/blog/extract-improvement-signals-from-negative-reviews", priority: 0.7, changeFrequency: "monthly" as const },
  { path: "/blog/5-key-metrics-for-cross-border-review-analysis", priority: 0.7, changeFrequency: "monthly" as const },
  { path: "/blog/ai-driven-product-iteration-closed-loop", priority: 0.7, changeFrequency: "monthly" as const },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();

  return [...marketingRoutes, ...blogRoutes].map((route) => ({
    url: absoluteUrl(route.path),
    lastModified,
    changeFrequency: route.changeFrequency,
    priority: route.priority,
  }));
}
