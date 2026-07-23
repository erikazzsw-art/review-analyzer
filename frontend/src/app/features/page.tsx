import { BottomCta } from "@/components/marketing/bottom-cta";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { buildMarketingMetadata } from "@/lib/seo";

import { FeaturesContent } from "./features-content";

export const metadata = buildMarketingMetadata({
  title: "ClueAI Features",
  description:
    "Explore ClueAI modules for turning customer reviews into pain point discovery, competitor opportunities, team actions, notifications, and follow-up validation.",
  path: "/features",
});

export default function FeaturesPage() {
  return (
    <>
      <SiteHeader />
      <FeaturesContent />
      <BottomCta />
      <SiteFooter />
    </>
  );
}
