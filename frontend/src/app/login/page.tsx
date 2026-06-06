import { CtaRow } from "@/components/marketing/cta-row";
import { HeroPreview } from "@/components/marketing/hero-preview";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Log In | ClueAI",
  description: "Access the authenticated ClueAI workspace.",
});

export default function LoginPage() {
  return (
    <MarketingShell
      eyebrow="Log in"
      title="Return to your review workspace without losing the current thread."
      description="The production login form will be connected in NX-M2. For now, this page anchors the layout, hierarchy, and visual language for the future authenticated shell."
      aside={<HeroPreview />}
    >
      <div className="space-y-4">
        <div className="rounded-card border border-line bg-white/82 p-5 text-sm leading-7 text-soft">
          Your dashboard, product groups, action center, and follow-up trackers
          will all live behind the same authenticated application shell.
        </div>
        <CtaRow
          primaryHref="/register"
          primaryLabel="Create New Account"
          secondaryHref="/trial"
          secondaryLabel="Preview the Trial Flow"
        />
      </div>
    </MarketingShell>
  );
}
