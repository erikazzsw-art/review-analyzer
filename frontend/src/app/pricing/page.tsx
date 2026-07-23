import { BottomCta } from "@/components/marketing/bottom-cta";
import { PricingFaq } from "@/components/marketing/pricing-faq";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { buildMarketingMetadata } from "@/lib/seo";

import PricingContent from "./pricing-content";

export const metadata = buildMarketingMetadata({
  title: "ClueAI Pricing",
  description:
    "Pricing for e-commerce sellers turning reviews into growth decisions. Start with 3,000 free credits for 14 days, no credit card required.",
  path: "/pricing",
});

export default function PricingPage() {
  return (
    <>
      <SiteHeader />
      <PricingContent />
      <PricingFaq />
      <BottomCta />
      <SiteFooter />
    </>
  );
}
