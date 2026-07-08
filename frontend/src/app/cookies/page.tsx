import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { LegalArticle } from "@/components/legal/legal-article";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("legal.cookies");
  return buildMarketingMetadata({
    title: t("pageTitle"),
    description: t("pageSubtitle"),
    path: "/cookies",
  });
}

export default async function CookiesPage() {
  const t = await getTranslations("legal.cookies");
  return (
    <MarketingShell title={t("pageTitle")} description={t("pageSubtitle")}>
      <LegalArticle page="cookies" />
    </MarketingShell>
  );
}
