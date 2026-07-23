import Link from "next/link";
import type { ReactNode } from "react";
import { useTranslations } from "next-intl";

function AuthShowcase() {
  const t = useTranslations("auth");
  return (
    <div className="rounded-card border border-line bg-white/80 p-6 shadow-card backdrop-blur">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-widest text-soft">
          {t("showcaseTitle")}
        </span>
        <span className="rounded-pill bg-[#e8f8f4] px-2 py-0.5 text-[10px] font-bold text-[#2e9680]">
          {t("showcaseLive")}
        </span>
      </div>
      <svg className="w-full" viewBox="0 0 280 120" fill="none">
        <line x1="0" y1="100" x2="280" y2="100" stroke="var(--line)" strokeWidth="0.5" />
        <line x1="0" y1="70" x2="280" y2="70" stroke="var(--line)" strokeWidth="0.5" />
        <line x1="0" y1="40" x2="280" y2="40" stroke="var(--line)" strokeWidth="0.5" />
        {/* 正面评论趋势 */}
        <polyline
          points="0,65 40,58 80,52 120,48 160,42 200,35 240,30 280,22"
          stroke="var(--mint)"
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
        />
        {/* 负面评论趋势 */}
        <polyline
          points="0,40 40,45 80,50 120,58 160,65 200,72 240,78 280,82"
          stroke="var(--rose)"
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
          opacity="0.7"
        />
        {/* 改进措施数 */}
        <polyline
          points="0,90 40,85 80,75 120,68 160,55 200,50 240,45 280,40"
          stroke="var(--lavender)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeDasharray="4,3"
          fill="none"
          opacity="0.7"
        />
      </svg>
      <div className="mt-3 flex gap-4 text-[10px] text-soft">
        <span className="flex items-center gap-1">
          <span className="inline-block h-1.5 w-3 rounded-full bg-mint" /> {t("showcasePositive")}
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-1.5 w-3 rounded-full bg-rose" /> {t("showcaseNegative")}
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-1.5 w-3 rounded-full bg-lavender" /> {t("showcaseActions")}
        </span>
      </div>
    </div>
  );
}

type AuthLayoutProps = {
  children: ReactNode;
};

export function AuthLayout({ children }: AuthLayoutProps) {
  const t = useTranslations("auth");
  return (
    <div className="flex min-h-screen">
      {/* Left: Product showcase */}
      <div className="relative hidden flex-1 flex-col justify-between overflow-hidden bg-[linear-gradient(160deg,#fff6f7_0%,#f8f4ff_50%,#eef9f6_100%)] p-10 lg:flex">
        {/* Logo */}
        <Link href="/" className="inline-flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-xs font-extrabold text-white">
            CA
          </span>
          <span className="font-heading text-lg font-bold tracking-normal text-ink">
            ClueAI
          </span>
        </Link>

        {/* Center: Data visualization */}
        <div className="mx-auto w-full max-w-md">
          <AuthShowcase />
        </div>

        {/* Bottom: Value proposition */}
        <div className="max-w-sm">
          <h2 className="font-heading text-xl font-bold text-ink">
            {t("showcaseHeading")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-soft">
            {t("showcaseBody")}
          </p>
        </div>

        {/* Background decorative gradient */}
        <div className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-lavender/10 blur-[100px]" />
        <div className="pointer-events-none absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-rose/10 blur-[80px]" />
      </div>

      {/* Right: Form area */}
      <div className="flex flex-1 flex-col items-center justify-center bg-white px-6 py-12 lg:max-w-[520px]">
        {/* Mobile logo */}
        <Link href="/" className="mb-8 inline-flex items-center gap-3 lg:hidden">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-xs font-extrabold text-white">
            CA
          </span>
          <span className="font-heading text-lg font-bold tracking-normal text-ink">
            ClueAI
          </span>
        </Link>

        <div className="w-full max-w-sm">{children}</div>
      </div>
    </div>
  );
}
