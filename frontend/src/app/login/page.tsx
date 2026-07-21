import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useTranslations } from "next-intl";
import { getTranslations } from "next-intl/server";

import { LoginForm } from "@/components/auth/login-form";
import { buildNoIndexMetadata } from "@/lib/seo";

export async function generateMetadata() {
  const t = await getTranslations("auth");
  return buildNoIndexMetadata({
    title: t("loginMetaTitle"),
    description: t("loginMetaDescription"),
  });
}

export default function LoginPage() {
  const t = useTranslations("auth");

  return (
    <div className="flex min-h-screen">
      {/* Left 50%: dark gradient + logo + "欢迎回来" */}
      <section
        className="relative hidden flex-1 flex-col items-center justify-center overflow-hidden lg:flex"
        style={{
          background: "linear-gradient(180deg, #4a2d8a 0%, #25212a 100%)",
        }}
      >
        {/* Floating decorative blobs */}
        <div
          className="pointer-events-none absolute -right-20 -top-20 h-[300px] w-[300px] rounded-full opacity-25 blur-[100px]"
          style={{ background: "#7c5cbf" }}
        />
        <div
          className="pointer-events-none absolute -bottom-16 -left-16 h-[250px] w-[250px] rounded-full opacity-20 blur-[80px]"
          style={{ background: "#4a2d8a" }}
        />

        {/* Content */}
        <div className="relative z-10 flex flex-col items-center text-center">
          {/* Logo */}
          <Link href="/" className="inline-flex items-center gap-3 mb-8">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-xs font-extrabold text-white shadow-sm">
              RL
            </span>
            <span className="font-heading text-lg font-extrabold tracking-[-0.02em] text-white">
              ReviewLens
            </span>
          </Link>

          {/* "欢迎回来" */}
          <h1 className="font-heading text-[40px] font-extrabold tracking-[-0.02em] text-white leading-tight">
            {t("loginTitle")}
          </h1>
          <p className="mt-3 text-base text-white/65">
            {t("loginSubtitle")}
          </p>
        </div>
      </section>

      {/* Right 50%: cream background + form */}
      <section className="flex flex-1 items-center justify-center bg-[#fffaf8] px-6 py-12 lg:px-10">
        <div className="w-full max-w-[384px]">
          {/* Mobile logo */}
          <Link href="/" className="mb-8 inline-flex items-center gap-3 lg:hidden">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-xs font-extrabold text-white">
              RL
            </span>
            <span className="font-heading text-lg font-extrabold tracking-[-0.02em] text-[#25212a]">
              ReviewLens
            </span>
          </Link>

          {/* Back to home */}
          <Link
            href="/"
            className="mb-6 inline-flex items-center gap-2 rounded-[12px] border border-[rgba(0,0,0,0.06)] bg-white px-4 py-2 text-sm font-semibold text-[#6f6877] shadow-sm transition hover:border-[rgba(0,0,0,0.12)] hover:text-[#25212a]"
          >
            <ArrowLeft className="h-4 w-4" />
            {t("backToHome")}
          </Link>

          {/* Heading — mobile only; desktop shows it on the left panel */}
          <div className="mb-6 lg:hidden">
            <h1 className="font-heading text-[28px] font-extrabold tracking-[-0.02em] text-[#25212a]">
              {t("loginTitle")}
            </h1>
            <p className="mt-2 text-base text-[#6f6877]">
              {t("loginSubtitle")}
            </p>
          </div>

          <LoginForm />
        </div>
      </section>
    </div>
  );
}
