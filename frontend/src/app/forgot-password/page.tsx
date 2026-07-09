import Link from "next/link";
import { useTranslations } from "next-intl";
import { getTranslations } from "next-intl/server";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";
import { AuthLayout } from "@/components/auth/auth-layout";
import { buildNoIndexMetadata } from "@/lib/seo";

export async function generateMetadata() {
  const t = await getTranslations("auth");
  return buildNoIndexMetadata({
    title: t("forgotMetaTitle"),
    description: t("forgotMetaDescription"),
  });
}

export default function ForgotPasswordPage() {
  const t = useTranslations("auth");

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-[-0.02em] text-ink">
            {t("forgotTitle")}
          </h1>
          <p className="mt-2 text-sm text-soft">
            {t("forgotSubtitle")}
          </p>
        </div>

        <ForgotPasswordForm />

        <p className="text-center text-sm text-soft">
          {t("hasAccount")}
          <Link href="/login" className="ml-1 font-semibold text-ink hover:underline">
            {t("goLogin")}
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
