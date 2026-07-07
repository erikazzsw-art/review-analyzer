export type PlanKey = "free" | "starter" | "pro" | "team";
export type BillingPeriod = "monthly" | "annual";

export type PlanPricing = {
  key: PlanKey;
  name: string;
  monthlyUsd: number;
  annualMonthlyUsd: number;
  annualTotalUsd: number;
  credits: number;
  contactOnly: boolean;
};

export type AddOn = {
  credits: number;
  priceUsd: number;
};

export const PLANS: Record<PlanKey, PlanPricing> = {
  free: {
    key: "free",
    name: "Free",
    monthlyUsd: 0,
    annualMonthlyUsd: 0,
    annualTotalUsd: 0,
    credits: 300,
    contactOnly: false,
  },
  starter: {
    key: "starter",
    name: "Starter",
    monthlyUsd: 12,
    annualMonthlyUsd: 9.6,
    annualTotalUsd: 115,
    credits: 5000,
    contactOnly: false,
  },
  pro: {
    key: "pro",
    name: "Pro",
    monthlyUsd: 29,
    annualMonthlyUsd: 23.2,
    annualTotalUsd: 278,
    credits: 15000,
    contactOnly: false,
  },
  team: {
    key: "team",
    name: "Team",
    monthlyUsd: 59,
    annualMonthlyUsd: 47.2,
    annualTotalUsd: 566,
    credits: 45000,
    contactOnly: false,
  },
};

export const ADD_ONS: AddOn[] = [
  { credits: 5000, priceUsd: 9 },
  { credits: 10000, priceUsd: 18 },
  { credits: 50000, priceUsd: 79 },
];

export const MONTHLY_GRANT: Record<PlanKey, number> = {
  free: 300,
  starter: 5000,
  pro: 15000,
  team: 45000,
};

export const CREDIT_COSTS = {
  review_analyze: 1,
  ask: 3,
  insight: 6,
  copywriter: 2,
  translate: 1,
  export: 1,
  competitor: 10,
  webhook: 0,
} as const;

export const TRIAL_CREDITS = 3000;
export const TRIAL_DAYS = 14;

export function getPlanPrice(plan: PlanPricing, period: BillingPeriod): number {
  return period === "annual" ? plan.annualMonthlyUsd : plan.monthlyUsd;
}

export function formatPrice(plan: PlanPricing, period: BillingPeriod): string {
  if (plan.contactOnly || plan.key === "team") return "Contact us";
  if (plan.monthlyUsd === 0) return "$0";
  const price = getPlanPrice(plan, period);
  return `$${price % 1 === 0 ? price : price.toFixed(1)}`;
}
