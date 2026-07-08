import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { LegalArticle } from "@/components/legal/legal-article";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("legal.refund");
  return buildMarketingMetadata({
    title: `${t("pageTitle")} | ClueAI`,
    description: t("pageSubtitle"),
    path: "/refund",
  });
}

export default async function RefundPage() {
  const t = await getTranslations("legal.refund");
  return (
    <MarketingShell title={t("pageTitle")} description={t("pageSubtitle")}>
      <LegalArticle page="refund" />
    </MarketingShell>
  );
}
