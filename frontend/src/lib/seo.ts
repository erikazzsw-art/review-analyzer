import type { Metadata } from "next";

const DEFAULT_SITE_URL = "https://clueai.com";
const DEFAULT_APP_URL = "https://app.clueai.com";
const DEFAULT_OG_IMAGE_PATH = "/opengraph-image";

function normalizeUrl(value: string | undefined, fallback: string): string {
  if (!value) {
    return fallback;
  }

  try {
    return new URL(value).origin;
  } catch {
    return fallback;
  }
}

export const siteUrl = normalizeUrl(
  process.env.NEXT_PUBLIC_SITE_URL ?? process.env.SITE_URL,
  DEFAULT_SITE_URL,
);

export const appUrl = normalizeUrl(
  process.env.NEXT_PUBLIC_APP_URL ?? process.env.APP_URL,
  DEFAULT_APP_URL,
);

export const ogImagePath = DEFAULT_OG_IMAGE_PATH;

export function absoluteUrl(path: string, baseUrl: string = siteUrl): string {
  return new URL(path, baseUrl).toString();
}

export function buildMarketingMetadata(input: {
  title: string;
  description: string;
  path: string;
}): Metadata {
  const canonicalUrl = absoluteUrl(input.path);
  const imageUrl = absoluteUrl(ogImagePath);

  return {
    title: input.title,
    description: input.description,
    alternates: {
      canonical: canonicalUrl,
    },
    openGraph: {
      title: input.title,
      description: input.description,
      url: canonicalUrl,
      siteName: "ClueAI",
      type: "website",
      images: [
        {
          url: imageUrl,
          width: 1200,
          height: 630,
          alt: "ClueAI marketing preview",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: input.title,
      description: input.description,
      images: [imageUrl],
    },
    keywords: [
      "ClueAI",
      "review analysis",
      "cross-border sellers",
      "Amazon reviews",
      "Walmart reviews",
      "product feedback",
      "action tracking",
    ],
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        "max-image-preview": "large",
        "max-snippet": -1,
        "max-video-preview": -1,
      },
    },
  };
}

export function buildNoIndexMetadata(input: {
  title: string;
  description: string;
}): Metadata {
  return {
    title: input.title,
    description: input.description,
    robots: {
      index: false,
      follow: false,
      nocache: true,
      googleBot: {
        index: false,
        follow: false,
        noimageindex: true,
        "max-image-preview": "none",
        "max-snippet": 0,
        "max-video-preview": 0,
      },
    },
  };
}
