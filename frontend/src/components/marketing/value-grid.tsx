const items = [
  {
    title: "See what deserves attention first",
    description:
      "Review uploads should immediately show which issue is rising, which SKU is at risk, and where the next action belongs.",
  },
  {
    title: "Turn findings into team actions",
    description:
      "The product is not just a summary view. It is meant to connect insight, ownership, and the next follow-up step.",
  },
  {
    title: "Validate whether changes worked",
    description:
      "Later review batches should confirm whether packaging, listing, structural, or feature changes actually improved the feedback.",
  },
];

export function ValueGrid() {
  return (
    <section className="grid gap-4 md:grid-cols-3">
      {items.map((item, index) => (
        <article
          key={item.title}
          className="rounded-card border border-line bg-white/84 px-6 py-6 shadow-card"
        >
          <div className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-roseSoft text-sm font-bold text-[#d94d72]">
            {index + 1}
          </div>
          <h2 className="mt-4 font-heading text-2xl font-bold tracking-[-0.03em] text-ink">
            {item.title}
          </h2>
          <p className="mt-3 text-sm leading-7 text-soft">{item.description}</p>
        </article>
      ))}
    </section>
  );
}
