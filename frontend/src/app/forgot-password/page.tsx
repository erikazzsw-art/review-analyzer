import Link from "next/link";
import { useTranslations } from "next-intl";
import { getTranslations } from "next-intl/server";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";
import { buildNoIndexMetadata } from "@/lib/seo";

export async function generateMetadata() {
  const t = await getTranslations("auth");
  return buildNoIndexMetadata({
    title: t("forgotMetaTitle"),
    description: t("forgotMetaDescription"),
  });
}

function LockIcon() {
  return (
    <svg
      width="40"
      height="40"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--rose)"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

export default function ForgotPasswordPage() {
  const t = useTranslations("auth");

  return (
    <div className="page-bg-warm relative flex min-h-screen items-center justify-center overflow-hidden">
      {/* V3 浮动 blob 装饰 */}
      <div className="blob-rose pointer-events-none absolute -top-32 -left-32 z-0" />
      <div className="blob-lavender pointer-events-none absolute top-32 -right-24 z-0" />

      {/* Logo — top left */}
      <Link
        href="/"
        className="absolute top-8 left-8 z-10 inline-flex items-center gap-3"
      >
        <span className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-xs font-extrabold text-white">
          RL
        </span>
        <span className="font-heading text-lg font-bold tracking-[-0.02em] text-ink">
          ReviewLens
        </span>
      </Link>

      {/* Centered glass card */}
      <div className="glass-white relative z-10 mx-4 w-full max-w-[440px] p-8">
        {/* Lock icon — rose circle */}
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-rose/10">
          <LockIcon />
        </div>

        {/* Title */}
        <h1 className="text-center font-heading text-2xl font-bold tracking-[-0.02em] text-ink">
          {t("forgotPassword")}
        </h1>
        <p className="mt-2 text-center text-sm leading-relaxed text-soft">
          {t("forgotSubtitle")}
        </p>

        {/* Form */}
        <div className="mt-6">
          <ForgotPasswordForm />
        </div>
      </div>

      {/* Bottom link: back to login */}
      <p className="absolute bottom-8 left-0 right-0 z-10 text-center text-sm text-soft">
        {t("hasAccount")}
        <Link
          href="/login"
          className="ml-1 font-semibold text-ink hover:underline"
        >
          {t("goLogin")}
        </Link>
      </p>
    </div>
  );
}
