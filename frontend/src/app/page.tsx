import { CtaRow } from "@/components/marketing/cta-row";
import { HeroPreview } from "@/components/marketing/hero-preview";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { ValueGrid } from "@/components/marketing/value-grid";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Review analysis for cross-border sellers",
  description:
    "ClueAI turns review signals into product, listing, and QA actions, then validates whether the changes worked.",
  path: "/",
});

export default function HomePage() {
  return (
    <div className="bg-hero-wash">
      <MarketingShell
        eyebrow="Review insight -> action -> validation"
        title="See what deserves your attention first, directly from your reviews."
        description="ClueAI is built for cross-border sellers who need more than sentiment summaries. It helps turn rising review issues into product, listing, and QA actions, then uses later comments to confirm whether those changes actually worked."
        aside={<HeroPreview />}
      >
        <div className="space-y-6">
          <div className="grid gap-3 text-sm text-soft sm:grid-cols-3">
            <div className="rounded-card border border-line bg-white/78 px-4 py-4">
              High-risk SKU detection
            </div>
            <div className="rounded-card border border-line bg-white/78 px-4 py-4">
              Action Center handoff
            </div>
            <div className="rounded-card border border-line bg-white/78 px-4 py-4">
              Follow-up validation loop
            </div>
          </div>
          <CtaRow
            primaryLabel="Create Account"
            secondaryLabel="Try the Flow First"
          />
        </div>
      </MarketingShell>

      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 pb-20 lg:px-10">
        <ValueGrid />
      </div>
    </div>
  );
}
