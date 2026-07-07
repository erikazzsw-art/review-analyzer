import { PricingFaq } from "@/components/marketing/pricing-faq";
import { buildMarketingMetadata } from "@/lib/seo";

import PricingContent from "./pricing-content";

export const metadata = buildMarketingMetadata({
  title: "Pricing | ClueAI ReviewLens",
  description:
    "Simple, transparent pricing for e-commerce review analysis. Start with 3,000 free credits — 14 days, no credit card required.",
  path: "/pricing",
});

export default function PricingPage() {
  return (
    <>
      <PricingContent />
      <PricingFaq />
    </>
  );
}
