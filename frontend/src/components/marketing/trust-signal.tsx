const platforms = [
  { name: "Amazon", icon: "🛒" },
  { name: "eBay", icon: "🏷️" },
  { name: "Shopee", icon: "🧡" },
  { name: "AliExpress", icon: "📦" },
  { name: "Walmart", icon: "🏪" },
  { name: "TikTok Shop", icon: "🎵" },
];

export function TrustSignal() {
  return (
    <section className="mx-auto w-full max-w-7xl px-6 pb-12 lg:px-10">
      <p className="text-center text-xs font-semibold uppercase tracking-[0.15em] text-soft">
        已支持主流跨境电商平台
      </p>
      <div className="mt-5 flex flex-wrap items-center justify-center gap-6 md:gap-10">
        {platforms.map((platform) => (
          <div
            key={platform.name}
            className="flex items-center gap-2 rounded-pill border border-line bg-white/80 px-4 py-2 text-sm font-medium text-soft shadow-sm"
          >
            <span className="text-base">{platform.icon}</span>
            <span>{platform.name}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
