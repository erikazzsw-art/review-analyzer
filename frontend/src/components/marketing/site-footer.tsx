import Link from "next/link";
import { useTranslations } from "next-intl";

const LEGAL_LINKS = [
  { href: "/privacy", key: "privacy" },
  { href: "/terms", key: "terms" },
  { href: "/cookies", key: "cookies" },
  { href: "/dpa", key: "dpa" },
  { href: "/sub-processors", key: "subProcessors" },
  { href: "/contact", key: "contact" },
] as const;

export function SiteFooter() {
  const t = useTranslations("footer");
  const year = new Date().getFullYear();

  return (
    <footer className="mx-auto w-full max-w-7xl px-6 pb-10 lg:px-10">
      <div className="border-t border-line pt-6">
        <nav
          aria-label="Legal"
          className="flex flex-wrap items-center gap-x-5 gap-y-2"
        >
          {LEGAL_LINKS.map(({ href, key }) => (
            <Link
              key={href}
              href={href}
              className="text-xs font-medium text-soft transition-colors hover:text-ink"
            >
              {t(key)}
            </Link>
          ))}
        </nav>
        <p className="mt-4 max-w-2xl text-[11px] leading-relaxed text-muted-foreground/80">
          {t("amazonDisclaimer")}
        </p>
        <p className="mt-2 text-[11px] text-muted-foreground/60">
          © {year} ClueAI. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
