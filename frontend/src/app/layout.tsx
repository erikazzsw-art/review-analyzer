import type { Metadata } from "next";

import "@/app/globals.css";
import { ogImagePath, siteUrl } from "@/lib/seo";
import { AnalyticsProvider } from "@/components/app/AnalyticsProvider";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "ClueAI",
    template: "%s | ClueAI",
  },
  description:
    "ClueAI helps cross-border sellers turn review signals into actions and follow-up validation.",
  openGraph: {
    title: "ClueAI",
    description:
      "ClueAI helps cross-border sellers turn review signals into actions and follow-up validation.",
    siteName: "ClueAI",
    type: "website",
    images: [
      {
        url: ogImagePath,
        width: 1200,
        height: 630,
        alt: "ClueAI",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "ClueAI",
    description:
      "ClueAI helps cross-border sellers turn review signals into actions and follow-up validation.",
    images: [ogImagePath],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AnalyticsProvider>{children}</AnalyticsProvider>
      </body>
    </html>
  );
}
