import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";

import "@/app/globals.css";
import { getMetadataBaseUrl, ogImagePath } from "@/lib/seo";
import { AnalyticsProvider } from "@/components/app/AnalyticsProvider";
import { CookieBanner } from "@/components/CookieBanner";

export const metadata: Metadata = {
  metadataBase: getMetadataBaseUrl(),
  title: {
    default: "ClueAI",
    template: "%s | ClueAI",
  },
  description:
    "ClueAI helps e-commerce sellers turn customer reviews into growth decisions, team notifications, and follow-up validation.",
  openGraph: {
    title: "ClueAI",
    description:
      "ClueAI helps e-commerce sellers turn customer reviews into growth decisions, team notifications, and follow-up validation.",
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
      "ClueAI helps e-commerce sellers turn customer reviews into growth decisions, team notifications, and follow-up validation.",
    images: [ogImagePath],
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} dir="ltr">
      <head>
        <meta
          httpEquiv="Cache-Control"
          content="no-store, no-cache, must-revalidate, proxy-revalidate"
        />
        <meta httpEquiv="Pragma" content="no-cache" />
        <meta httpEquiv="Expires" content="0" />
      </head>
      <body>
        <NextIntlClientProvider messages={messages}>
          <AnalyticsProvider>{children}</AnalyticsProvider>
          <CookieBanner />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
