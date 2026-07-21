"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { ArrowRight } from "lucide-react";

import { LocaleSwitcher } from "@/components/ui/locale-switcher";

type FooterColumn = {
  titleKey: string;
  links: { href: string; labelKey: string }[];
};

const PRODUCT_LINKS: FooterColumn["links"] = [
  { href: "/features", labelKey: "productFeatures" },
  { href: "/pricing", labelKey: "productPricing" },
  { href: "/extension", labelKey: "productExtension" },
];

const RESOURCE_LINKS: FooterColumn["links"] = [
  { href: "/blog", labelKey: "resourceBlog" },
  { href: "/case-studies", labelKey: "resourceCases" },
  { href: "/qa", labelKey: "resourceQa" },
  { href: "/api-docs", labelKey: "resourceApi" },
];

const COMPANY_LINKS: FooterColumn["links"] = [
  { href: "/contact", labelKey: "companyContact" },
  { href: "/privacy", labelKey: "companyPrivacy" },
  { href: "/terms", labelKey: "companyTerms" },
];

const COLUMNS: FooterColumn[] = [
  { titleKey: "products", links: PRODUCT_LINKS },
  { titleKey: "resources", links: RESOURCE_LINKS },
  { titleKey: "company", links: COMPANY_LINKS },
];

export function SiteFooter() {
  const t = useTranslations("footer");
  const year = new Date().getFullYear();
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function handleSubscribe(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    // TODO: wire to newsletter backend
    setSubmitted(true);
    setEmail("");
  }

  return (
    <footer className="relative overflow-hidden bg-ink">
      {/* Top blur rose blob */}
      <div
        className="pointer-events-none absolute -top-24 left-1/2 z-0 h-80 w-[600px] -translate-x-1/2"
        style={{
          background:
            "radial-gradient(ellipse 50% 50% at 50% 0%, rgba(243,111,143,0.35) 0%, transparent 70%)",
        }}
      />

      {/* Main 4-column grid */}
      <div className="relative z-10 mx-auto grid max-w-7xl grid-cols-1 gap-10 px-6 pb-12 pt-16 sm:grid-cols-2 lg:grid-cols-4 lg:px-10">
        {/* Link columns */}
        {COLUMNS.map((col) => (
          <div key={col.titleKey}>
            <h3 className="font-heading text-sm font-bold uppercase tracking-[0.08em] text-white/90">
              {t(col.titleKey)}
            </h3>
            <ul className="mt-5 space-y-3">
              {col.links.map((link) => (
                <li key={link.labelKey}>
                  <Link
                    href={link.href}
                    className="text-sm text-white/55 transition-colors hover:text-white/85"
                  >
                    {t(link.labelKey)}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}

        {/* Subscribe column */}
        <div>
          <h3 className="font-heading text-sm font-bold uppercase tracking-[0.08em] text-white/90">
            {t("subscribe")}
          </h3>
          <p className="mt-5 text-sm leading-relaxed text-white/55">
            {t("subscribeDesc")}
          </p>
          {submitted ? (
            <p className="mt-4 text-sm font-medium text-mint">
              {t("subscribeSuccess")}
            </p>
          ) : (
            <form onSubmit={handleSubscribe} className="mt-4 flex gap-2">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("emailPlaceholder")}
                className="min-w-0 flex-1 rounded-xl border border-white/15 bg-white/8 px-3.5 py-2.5 text-sm text-white placeholder:text-white/30 outline-none transition focus:border-rose/50 focus:bg-white/12"
              />
              <button
                type="submit"
                className="inline-flex shrink-0 items-center justify-center rounded-xl bg-rose px-3.5 py-2.5 text-sm font-semibold text-white transition hover:bg-rose/85 active:scale-95"
                aria-label={t("subscribeButton")}
              >
                <ArrowRight className="h-4 w-4" />
              </button>
            </form>
          )}
        </div>
      </div>

      {/* Bottom bar */}
      <div className="relative z-10 border-t border-white/8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-6 py-5 sm:flex-row lg:px-10">
          <p className="text-xs text-white/40">
            {t("copyright").replace("2026", String(year))}
          </p>
          <LocaleSwitcher />
        </div>
      </div>
    </footer>
  );
}
