import Link from "next/link";

import { Button } from "@/components/ui/button";

const navItems = [
  { href: "/pricing", label: "Pricing" },
  { href: "/trial", label: "Try the Flow" },
  { href: "/login", label: "Log In" },
];

export function SiteHeader() {
  return (
    <header className="mx-auto flex w-full max-w-7xl items-center justify-between gap-6 px-6 py-6 lg:px-10">
      <Link
        href="/"
        className="inline-flex items-center gap-3 rounded-pill border border-line/80 bg-white/70 px-4 py-2 shadow-glow backdrop-blur"
      >
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-[16px] bg-[linear-gradient(135deg,#f36f8f,#8d7be8)] font-heading text-sm font-extrabold text-white">
          CA
        </span>
        <span>
          <strong className="block font-heading text-lg tracking-[-0.02em] text-ink">
            ClueAI
          </strong>
          <span className="block text-xs text-soft">
            Review intelligence for sellers
          </span>
        </span>
      </Link>

      <nav className="hidden items-center gap-3 md:flex">
        {navItems.map((item) => (
          <Button key={item.href} variant="ghost" asChild className="rounded-pill px-4 py-2 text-sm font-semibold text-soft hover:border-line hover:bg-white/80 hover:text-ink">
            <Link href={item.href}>{item.label}</Link>
          </Button>
        ))}
        <Button asChild className="rounded-pill bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 hover:bg-ink/90">
          <Link href="/register">Create Account</Link>
        </Button>
      </nav>
    </header>
  );
}
