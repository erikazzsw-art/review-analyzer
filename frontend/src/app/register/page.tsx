import Link from "next/link";
import { Suspense } from "react";
import { useTranslations } from "next-intl";

import { RegisterForm } from "@/components/auth/register-form";
import { AuthLayout } from "@/components/auth/auth-layout";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "注册",
  description: "创建 ReviewLens 账号，开始智能评论分析。",
});

export default function RegisterPage() {
  const t = useTranslations("auth");

  return (
    <AuthLayout>
      <div className="space-y-6">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-[-0.02em] text-ink">
            {t("registerTitle")}
          </h1>
          <p className="mt-2 text-sm text-soft">
            {t("registerSubtitle")}
          </p>
        </div>

        <Suspense fallback={null}>
          <RegisterForm />
        </Suspense>

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
