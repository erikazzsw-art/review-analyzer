import Link from "next/link";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";
import { HeroPreview } from "@/components/marketing/hero-preview";
import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Forgot Password | ClueAI",
  description: "Reset your ClueAI account password.",
});

export default function ForgotPasswordPage() {
  return (
    <MarketingShell
      eyebrow="Forgot password"
      title="Reset your password via email verification."
      description="Enter your registered email to receive a verification code."
      aside={<HeroPreview />}
    >
      <div className="space-y-4">
        <ForgotPasswordForm />
        <p className="text-center text-sm text-soft">
          Remember your password?{" "}
          <Link href="/login" className="font-semibold text-ink hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </MarketingShell>
  );
}
