export default function PushSettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-6 pt-6 lg:px-10">
      <header className="pb-5">
        <h1 className="font-heading text-2xl font-extrabold tracking-[-0.03em] text-ink md:text-3xl">
          推送设置
        </h1>
        <p className="mt-1.5 text-sm leading-6 text-soft md:text-base">
          配置自动推送设置。
        </p>
      </header>
      {children}
    </div>
  );
}
