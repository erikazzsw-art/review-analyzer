import { CtaRow } from "@/components/marketing/cta-row";
import { HeroPreview } from "@/components/marketing/hero-preview";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Try the Flow",
  description:
    "Preview the full review-to-action flow before you register for the workspace.",
  path: "/trial",
});

export default function TrialPage() {
  return (
    <MarketingShell
      eyebrow="Trial"
      title="Let first-time users preview the flow before asking them to commit."
      description="The trial should preserve the real sequence: upload a batch, inspect the result, understand the issue pattern, then decide whether to register for the full workspace."
      aside={<HeroPreview />}
    >
      <div className="space-y-4">
        <div className="rounded-card border border-line bg-white/82 p-5 text-sm leading-7 text-soft">
          In later modules this page will route into a lightweight upload and
          analysis experience. For now it establishes the standalone landing
          route and responsive shell.
        </div>
        <CtaRow
          primaryHref="/register"
          primaryLabel="Unlock Full Workspace"
          secondaryHref="/pricing"
          secondaryLabel="See Plans"
        />
      </div>
    </MarketingShell>
  );
}
