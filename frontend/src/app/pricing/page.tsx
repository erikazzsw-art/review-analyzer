import { CtaRow } from "@/components/marketing/cta-row";
import { HeroPreview } from "@/components/marketing/hero-preview";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Pricing | ClueAI",
  description:
    "Compare Free, Pro, and Team plans for review analysis, review Q&A, and operational follow-up.",
  path: "/pricing",
});

const plans = [
  {
    name: "Free",
    price: "$0",
    points: ["1 product group", "Core review analysis", "Trial-friendly onboarding"],
  },
  {
    name: "Pro",
    price: "$39",
    points: ["Multi-product workflow", "Review Q&A", "Action and follow-up loop"],
  },
  {
    name: "Team",
    price: "Custom",
    points: ["Role workflows", "Operational handoff", "Commercial rollout support"],
  },
];

export default function PricingPage() {
  return (
    <div className="bg-hero-wash">
      <MarketingShell
        eyebrow="Pricing"
        title="Simple pricing that grows with your business."
        description="Start free. Upgrade when you need multi-product workflows, review Q&A, and action tracking."
        aside={<HeroPreview />}
      >
        <CtaRow
          primaryHref="/register"
          primaryLabel="Start Free"
          secondaryHref="/settings"
          secondaryLabel="Open Settings"
        />
      </MarketingShell>

      <div className="mx-auto grid w-full max-w-7xl gap-4 px-6 pb-20 lg:grid-cols-3 lg:px-10">
        {plans.map((plan) => (
          <article
            key={plan.name}
            className="rounded-shell border border-line bg-white/86 p-6 shadow-card"
          >
            <div className="text-sm font-semibold uppercase tracking-[0.12em] text-soft">
              {plan.name}
            </div>
            <div className="mt-3 font-heading text-5xl font-extrabold tracking-[-0.04em] text-ink">
              {plan.price}
            </div>
            <div className="mt-6 space-y-3 text-sm leading-7 text-soft">
              {plan.points.map((point) => (
                <div
                  key={point}
                  className="rounded-card border border-line bg-[#fffafb] px-4 py-3"
                >
                  {point}
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
