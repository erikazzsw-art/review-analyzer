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
  secondaryHref = "/login",
  secondaryLabel,
}: CtaRowProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <Button
        href={primaryHref}
        className="min-h-11 rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 hover:bg-ink/90"
      >
        {primaryLabel}
      </Button>
      <Button
        href={secondaryHref}
        variant="outline"
        className="min-h-11 rounded-pill border-line bg-white/86 px-5 py-3 text-sm font-semibold text-ink hover:border-[#d8cfde] hover:bg-white"
      >
        {secondaryLabel}
      </Button>
    </div>
  );
}
