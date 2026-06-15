import Link from "next/link";

import { Button } from "@/components/ui/button";

type CtaRowProps = {
  primaryHref?: string;
  primaryLabel: string;
  secondaryHref?: string;
  secondaryLabel: string;
};

export function CtaRow({
  primaryHref = "/register",
  primaryLabel,
  secondaryHref = "/trial",
  secondaryLabel,
}: CtaRowProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <Button asChild className="min-h-11 rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 hover:bg-ink/90">
        <Link href={primaryHref}>{primaryLabel}</Link>
      </Button>
      <Button variant="outline" asChild className="min-h-11 rounded-pill border-line bg-white/86 px-5 py-3 text-sm font-semibold text-ink hover:border-[#d8cfde] hover:bg-white">
        <Link href={secondaryHref}>{secondaryLabel}</Link>
      </Button>
    </div>
  );
}
