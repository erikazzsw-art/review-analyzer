const metrics = [
  { label: "Pending Follow-up", value: "07", tone: "bg-[#fff0f4] text-[#d94d72]" },
  { label: "Risk SKU Watch", value: "03", tone: "bg-[#eef6ff] text-[#4a7dc7]" },
];

const panels = [
  {
    title: "Today's Review Workspace",
    text: "Start from the highest-risk product group, not from a scattered feature menu.",
  },
  {
    title: "Action Center",
    text: "Turn recurring packaging, listing, or quality issues into owned team tasks in one step.",
  },
  {
    title: "Follow-up Validation",
    text: "Use later reviews to confirm whether an update actually reduced the complaint share.",
  },
];

export function HeroPreview() {
  return (
    <div className="flex h-full flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className="rounded-card border border-line bg-white px-5 py-5 shadow-sm"
          >
            <div className="text-xs font-semibold uppercase tracking-[0.1em] text-soft">
              {metric.label}
            </div>
            <div className="mt-3 flex items-end justify-between">
              <div className="font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
                {metric.value}
              </div>
              <div className={`rounded-pill px-3 py-1 text-xs font-bold ${metric.tone}`}>
                Live
              </div>
            </div>
            <div className="mt-4 h-2 rounded-pill bg-[linear-gradient(90deg,#f36f8f,#8d7be8)]" />
          </div>
        ))}
      </div>

      <div className="space-y-3 rounded-card border border-line bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(252,246,251,0.94))] p-4 shadow-sm">
        {panels.map((panel) => (
          <div key={panel.title} className="rounded-[20px] border border-line bg-white px-4 py-4">
            <div className="font-heading text-lg font-bold tracking-[-0.02em] text-ink">
              {panel.title}
            </div>
            <p className="mt-2 text-sm leading-7 text-soft">{panel.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
