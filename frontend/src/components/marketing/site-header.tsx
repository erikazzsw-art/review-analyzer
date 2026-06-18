import { Button } from "@/components/ui/button";
import { LocaleSwitcher } from "@/components/ui/locale-switcher";
import { useTranslations } from "next-intl";

export function SiteHeader() {
  const t = useTranslations("header");
  const tCommon = useTranslations("common");

  const navItems = [
    { href: "/pricing", label: t("pricing") },
    { href: "/trial", label: t("trial") },
    { href: "/login", label: t("login") },
  ];

  return (
    <header className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-6 py-6 lg:px-10">
      <a
        href="/"
        className="inline-flex items-center gap-3 rounded-pill border border-line/80 bg-white/70 px-4 py-2 shadow-glow backdrop-blur"
      >
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-[16px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-sm font-extrabold text-white">
          RL
        </span>
        <span>
          <strong className="block font-heading text-lg tracking-[-0.02em] text-ink">
            ReviewLens
          </strong>
          <span className="block text-xs text-soft">
            {tCommon("tagline")}
          </span>
        </span>
      </a>

      <nav className="flex items-center gap-2 md:gap-3">
        <LocaleSwitcher variant="header" />
        {navItems.map((item) => (
          <Button
            key={item.href}
            href={item.href}
            variant="ghost"
            className="rounded-pill px-4 py-2 text-sm font-semibold text-soft hover:border-line hover:bg-white/80 hover:text-ink"
          >
            {item.label}
          </Button>
        ))}
        <Button
          href="/register"
          className="rounded-pill bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 hover:bg-ink/90"
        >
          {t("register")}
        </Button>
      </nav>
    </header>
  );
}
