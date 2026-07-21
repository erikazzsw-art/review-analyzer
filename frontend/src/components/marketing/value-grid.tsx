import { useTranslations } from "next-intl";

export function ValueGrid() {
  const t = useTranslations("marketing");

  const items = [
    {
      title: t("value1Title"),
      description: t("value1Desc"),
      accent: "bg-roseSoft text-[#d94d72]",
    },
    {
      title: t("value2Title"),
      description: t("value2Desc"),
      accent: "bg-[#f0edff] text-[#6b5ce7]",
    },
    {
      title: t("value3Title"),
      description: t("value3Desc"),
      accent: "bg-[#e8f8f4] text-[#2e9680]",
    },
  ];

  return (
    <section className="grid gap-4 md:grid-cols-3">
      {items.map((item, index) => (
        <article
          key={item.title}
          className="rounded-card border border-line bg-white/84 px-6 py-6 shadow-card transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_8px_32px_rgba(0,0,0,0.1)]"
        >
          <div className={`inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold ${item.accent}`}>
            {index + 1}
          </div>
          <h2 className="mt-4 font-heading text-xl font-bold tracking-[-0.02em] text-ink">
            {item.title}
          </h2>
          <p className="mt-3 text-sm leading-7 text-soft">{item.description}</p>
        </article>
      ))}
    </section>
  );
}
