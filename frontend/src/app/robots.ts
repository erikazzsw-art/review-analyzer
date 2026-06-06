import type { MetadataRoute } from "next";

import { siteUrl } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/"],
        disallow: [
          "/login",
          "/register",
          "/workspace",
          "/products",
          "/upload",
          "/qa",
          "/actions",
          "/reviews",
          "/copywriter",
          "/settings",
          "/analysis",
        ],
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
    host: siteUrl,
  };
}
