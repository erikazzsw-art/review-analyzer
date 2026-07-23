import { getTranslations } from "next-intl/server";

export default async function PushSettingsLayout({ children }: { children: React.ReactNode }) {
  const t = await getTranslations("settings.layout");
  return (
    <div className="px-6 pt-6 lg:px-10">
      <header className="pb-5">
        <h1 className="font-heading text-2xl font-extrabold tracking-normal text-ink md:text-3xl">
          {t("pushSettingsTitle")}
        </h1>
        <p className="mt-1.5 text-sm leading-6 text-soft md:text-base">
          {t("pushSettingsDesc")}
        </p>
      </header>
      {children}
    </div>
  );
}
