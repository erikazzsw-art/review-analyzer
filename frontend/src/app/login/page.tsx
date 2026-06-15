import Link from "next/link";

import { LoginForm } from "@/components/auth/login-form";
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
      title="Return to your review workspace."
      description="Log in to access your dashboard, product groups, and action center."
      aside={<HeroPreview />}
    >
      <div className="space-y-4">
        <LoginForm />
        <p className="text-center text-sm text-soft">
          <Link href="/forgot-password" className="font-semibold text-ink hover:underline">
            Forgot password?
          </Link>
        </p>
        <p className="text-center text-sm text-soft">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-semibold text-ink hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </MarketingShell>
  );
}
