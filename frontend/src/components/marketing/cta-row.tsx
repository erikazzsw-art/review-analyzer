import Link from "next/link";

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
      <Link
        href={primaryHref}
        className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5"
      >
        {primaryLabel}
      </Link>
      <Link
        href={secondaryHref}
        className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white/86 px-5 py-3 text-sm font-semibold text-ink transition hover:border-[#d8cfde] hover:bg-white"
      >
        {secondaryLabel}
      </Link>
    </div>
  );
}
