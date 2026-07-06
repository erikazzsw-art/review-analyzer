export type PlanKey = "free" | "pro" | "team";

export type PlanPricing = {
  key: PlanKey;
  name: string;
  priceUsd: string;
  priceCnyApprox: string | null;
  originalPriceUsd: string | null;
  period: string;
  contactOnly: boolean;
};

export const PLANS: Record<PlanKey, PlanPricing> = {
  free: {
    key: "free",
    name: "Free",
    priceUsd: "$0",
    priceCnyApprox: null,
    originalPriceUsd: null,
    period: "永久免费",
    contactOnly: false,
  },
  pro: {
    key: "pro",
    name: "Pro",
    priceUsd: "$19",
    priceCnyApprox: "¥138",
    originalPriceUsd: null,
    period: "/月",
    contactOnly: false,
  },
  team: {
    key: "team",
    name: "Team",
    priceUsd: "联系我们",
    priceCnyApprox: null,
    originalPriceUsd: null,
    period: "",
    contactOnly: true,
  },
};

export function formatDualCurrency(plan: PlanPricing): string {
  if (plan.contactOnly) return plan.priceUsd;
  if (!plan.priceCnyApprox) return plan.priceUsd;
  return `${plan.priceUsd} / 约 ${plan.priceCnyApprox}`;
}
