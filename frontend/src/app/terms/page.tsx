import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { LegalArticle } from "@/components/legal/legal-article";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("legal.terms");
  return buildMarketingMetadata({
    title: `${t("pageTitle")} | ClueAI`,
    description: t("pageSubtitle"),
    path: "/terms",
  });
}

export default async function TermsPage() {
  const t = await getTranslations("legal.terms");
  return (
    <MarketingShell title={t("pageTitle")} description={t("pageSubtitle")}>
      <LegalArticle page="terms" />
    </MarketingShell>
  );
}
