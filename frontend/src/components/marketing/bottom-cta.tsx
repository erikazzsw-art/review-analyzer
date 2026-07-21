import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";

type BottomCtaProps = {
  text?: string;
  buttonLabel?: string;
  buttonHref?: string;
};

export function BottomCta({
  text,
  buttonLabel,
  buttonHref = "/register",
}: BottomCtaProps) {
  const t = useTranslations("marketing.bottomCta");

  return (
    <section className="mx-auto w-full max-w-7xl px-6 pb-20 lg:px-10">
      <div className="relative overflow-hidden rounded-[24px] bg-[linear-gradient(135deg,#f36f8f_0%,#8d7be8_100%)] px-8 py-14 text-center shadow-[0_8px_40px_rgba(243,111,143,0.3)]">
        {/* Decorative blobs */}
        <div className="pointer-events-none absolute -left-20 -top-20 h-64 w-64 rounded-full bg-white/8 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-16 -right-16 h-56 w-56 rounded-full bg-white/6 blur-3xl" />

        <h2 className="relative font-heading text-2xl font-extrabold tracking-[-0.02em] text-white md:text-[28px]">
          {text || t("text")}
        </h2>
        <div className="relative mt-8">
          <Button
            href={buttonHref}
            variant="ghost"
            size="marketing"
            className="bg-white text-[#f36f8f] hover:bg-white/95 hover:text-[#f36f8f] shadow-[0_4px_16px_rgba(0,0,0,0.1)]"
          >
            {buttonLabel || t("button")}
          </Button>
        </div>
      </div>
    </section>
  );
}
