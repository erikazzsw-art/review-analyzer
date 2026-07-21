import type { Metadata } from "next";
import { getMessages, getTranslations } from "next-intl/server";

import { LegalArticle } from "@/components/legal/legal-article";
import { LegalLayout, type TocItem } from "@/components/legal/legal-layout";
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
  const messages = await getMessages();
  const legal = messages.legal as Record<
    string,
    { sections?: { heading: string }[] }
  >;
  const content = legal.dpa;
  const tocItems: TocItem[] = (content?.sections ?? []).map((s, i) => ({
    id: `legal-section-${i}`,
    label: s.heading,
  }));

  return (
    <LegalLayout tocItems={tocItems}>
      <LegalArticle page="dpa" />
    </LegalLayout>
  );
}
