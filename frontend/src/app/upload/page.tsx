import { AppShell } from "@/components/app/app-shell";
import { UploadForm } from "@/components/upload/upload-form";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Upload",
  description: "Upload review data for analysis.",
});

export default async function UploadPage() {
  return (
    <AppShell
      currentPath="/upload"
      title="上传评论数据"
      description="支持 CSV / Excel / DOCX / TXT 文件，上传后自动启动 AI 分析。"
    >
      <UploadForm />
    </AppShell>
  );
}
