import { BottomCta } from "@/components/marketing/bottom-cta";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { buildMarketingMetadata } from "@/lib/seo";

import { FeaturesContent } from "./features-content";

export const metadata = buildMarketingMetadata({
  title: "ReviewLens Features",
  description:
    "Explore ReviewLens' six core modules — Dashboard, Ask AI, Review Analysis, Action Center, Version Compare, and Review Timeline — covering the full review analytics workflow.",
  path: "/features",
});

export default function FeaturesPage() {
  return (
    <>
      <SiteHeader />
      <FeaturesContent />
      <BottomCta text="准备试试？" buttonLabel="免费开始" />
      <SiteFooter />
    </>
  );
}
