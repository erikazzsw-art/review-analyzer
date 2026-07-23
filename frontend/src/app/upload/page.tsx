import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app/app-shell";
import { UploadForm } from "@/components/upload/upload-form";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Import Reviews",
  description: "Import review data to generate growth decision insights.",
});

export default async function UploadPage() {
  const t = await getTranslations("upload.page");
  return (
    <AppShell
      currentPath="/upload"
      title={t("title")}
      description={t("description")}
    >
      <UploadForm />
    </AppShell>
  );
}
