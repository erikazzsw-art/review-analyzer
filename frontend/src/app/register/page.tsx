import Link from "next/link";
import { Suspense } from "react";
import { useTranslations } from "next-intl";
import { getTranslations } from "next-intl/server";

import { RegisterForm } from "@/components/auth/register-form";
import { buildNoIndexMetadata } from "@/lib/seo";

export async function generateMetadata() {
  const t = await getTranslations("auth");
  return buildNoIndexMetadata({
    title: t("registerMetaTitle"),
    description: t("registerMetaDescription"),
  });
}

export default function RegisterPage() {
  const t = useTranslations("auth");
  const tMarketing = useTranslations("marketing");

  return (
    <div className="flex min-h-screen flex-col">
      {/* Top nav bar — 64px, fixed, glass-white */}
      <header className="sticky top-0 z-50 flex h-16 items-center border-b border-[rgba(0,0,0,0.06)] bg-white/80 backdrop-blur-[20px]">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 lg:px-10">
          {/* Logo */}
          <Link href="/" className="inline-flex items-center gap-2.5">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-xs font-extrabold text-white shadow-sm">
              CA
            </span>
            <span className="font-heading text-lg font-extrabold tracking-normal text-ink">
              ClueAI
            </span>
          </Link>

          {/* Right: "已有账户？登录" */}
          <p className="text-sm text-soft">
            {t("hasAccount")}
            <Link
              href="/login"
              className="ml-1 font-semibold text-[#f36f8f] hover:underline"
            >
              {t("goLogin")}
            </Link>
          </p>
        </div>
      </header>

      {/* Two-column content */}
      <div className="flex flex-1">
        {/* Left ~40%: form area — cream background */}
        <section className="flex flex-1 items-center justify-center bg-[#fffaf8] px-6 py-12 lg:px-10">
          <div className="w-full max-w-[384px]">
            <div className="mb-6">
              <h1 className="font-heading text-[28px] font-extrabold tracking-normal text-[#25212a]">
                {t("registerTitle")}
              </h1>
              <p className="mt-2 text-base text-[#6f6877]">
                {t("registerSubtitle")}
              </p>
            </div>

            <Suspense fallback={null}>
              <RegisterForm />
            </Suspense>
          </div>
        </section>

        {/* Right ~60%: testimonial — brand gradient + blobs */}
        <section className="relative hidden flex-1 flex-col items-center justify-center overflow-hidden lg:flex"
          style={{
            background: "linear-gradient(180deg, #f8f4ff 0%, #fff6f7 100%)",
          }}
        >
          {/* Floating decorative blobs */}
          <div
            className="pointer-events-none absolute -right-20 -top-20 h-[300px] w-[300px] rounded-full opacity-40 blur-[100px]"
            style={{ background: "#d8c8f0" }}
          />
          <div
            className="pointer-events-none absolute -bottom-16 -left-16 h-[250px] w-[250px] rounded-full opacity-40 blur-[80px]"
            style={{ background: "#f8c8d4" }}
          />

          {/* Testimonial content */}
          <div className="relative z-10 max-w-[480px] px-10 text-center">
            {/* Large quotation mark */}
            <span
              className="font-heading text-[72px] font-extrabold leading-none"
              style={{ color: "rgba(243,111,143,0.15)" }}
            >
              &ldquo;
            </span>

            {/* Quote text */}
            <blockquote className="mt-2 font-sans text-xl leading-relaxed text-[#25212a]">
              {tMarketing("testimonial.quote")}
            </blockquote>

            {/* Author row */}
            <div className="mt-6 flex items-center justify-center gap-3">
              {/* Avatar circle */}
              <span
                className="inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold text-white"
                style={{ background: "#f36f8f" }}
              >
                {tMarketing("testimonial.avatarInitial")}
              </span>
              <div className="text-left">
                <p className="text-sm font-semibold text-[#25212a]">
                  {tMarketing("testimonial.authorName")}
                </p>
                <p className="text-sm text-[#6f6877]">
                  {tMarketing("testimonial.authorTitle")}
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
