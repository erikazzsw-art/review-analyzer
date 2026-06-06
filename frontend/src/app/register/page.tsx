import { CtaRow } from "@/components/marketing/cta-row";
import { HeroPreview } from "@/components/marketing/hero-preview";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Create Account | ClueAI",
  description: "Create a ClueAI account and start with the review workspace.",
});

export default function RegisterPage() {
  return (
    <MarketingShell
      eyebrow="Create account"
      title="Start with one batch of reviews and make the next decision clearer."
      description="This page will later connect to the Python auth API. The first frontend milestone is to establish the complete acquisition and onboarding shell before wiring the forms."
      aside={<HeroPreview />}
    >
      <div className="space-y-4">
        <div className="rounded-card border border-line bg-white/82 p-5 text-sm leading-7 text-soft">
          Registration should lead directly into Today&apos;s Workspace so first-time
          users immediately see where to upload, what to analyze, and what
          should be handled next.
        </div>
        <CtaRow
          primaryLabel="Open Trial Instead"
          primaryHref="/trial"
          secondaryLabel="Already Have an Account"
          secondaryHref="/login"
        />
      </div>
    </MarketingShell>
  );
}
