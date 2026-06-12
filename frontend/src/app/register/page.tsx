import Link from "next/link";

import { RegisterForm } from "@/components/auth/register-form";
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
      description="Create your account to access the full review workspace."
      aside={<HeroPreview />}
    >
      <div className="space-y-4">
        <RegisterForm />
        <p className="text-center text-sm text-soft">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-ink hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </MarketingShell>
  );
}
