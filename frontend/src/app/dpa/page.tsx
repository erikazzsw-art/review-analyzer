import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { LegalArticle } from "@/components/legal/legal-article";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("legal.dpa");
  return buildMarketingMetadata({
    title: t("pageTitle"),
    description: t("pageSubtitle"),
    path: "/dpa",
  });
}

export default async function DpaPage() {
  const t = await getTranslations("legal.dpa");
  return (
    <MarketingShell title={t("pageTitle")} description={t("pageSubtitle")}>
      <LegalArticle page="dpa" />
    </MarketingShell>
  );
}
