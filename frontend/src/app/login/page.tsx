import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";

import { LoginForm } from "@/components/auth/login-form";
import { AuthLayout } from "@/components/auth/auth-layout";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "登录",
  description: "登录 ReviewLens，进入评论分析工作台。",
});

export default function LoginPage() {
  const t = useTranslations("auth");

  return (
    <AuthLayout>
      <div className="space-y-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-pill border border-line bg-white px-4 py-2 text-sm font-semibold text-soft shadow-sm transition hover:border-[#d8cfde] hover:text-ink"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("backToHome")}
        </Link>
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-[-0.02em] text-ink">
            {t("loginTitle")}
          </h1>
          <p className="mt-2 text-sm text-soft">
            {t("loginSubtitle")}
          </p>
        </div>

        <LoginForm />

        <div className="flex items-center justify-between text-sm">
          <Link href="/forgot-password" className="text-soft hover:text-ink hover:underline">
            {t("forgotPassword")}
          </Link>
          <p className="text-soft">
            {t("noAccount")}
            <Link href="/register" className="ml-1 font-semibold text-ink hover:underline">
              {t("goRegister")}
            </Link>
          </p>
        </div>
      </div>
    </AuthLayout>
  );
}
