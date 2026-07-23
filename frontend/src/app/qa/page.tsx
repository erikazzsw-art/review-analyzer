import Link from "next/link";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { QaPanel } from "@/components/analysis/qa-panel";
import { QaFaqAccordion } from "@/components/analysis/qa-faq-accordion";
import { getQaProducts, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Review Q&A",
  description: "Authenticated question answering over review evidence for growth decisions.",
});

export default async function QaPage() {
  try {
    const products = await getQaProducts();
    return (
      <AppShell
        currentPath="/qa"
        title="Ask Reviews"
        description=""
      >
        <QaPanel products={products} />
        <QaFaqAccordion />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 403) {
      return (
        <AppShell
          currentPath="/qa"
          title="Ask Reviews 需要 Pro 权限。"
          description="升级后可按产品聚合评论，围绕痛点、竞品机会和 Listing 线索继续追问。"
        >
          <section className="rounded-shell border border-dashed border-line bg-white/80 px-6 py-10 shadow-card backdrop-blur">
            <div className="inline-flex rounded-pill bg-[#fff1f5] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
              PRO FEATURE
            </div>
            <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
              升级后解锁 Ask Reviews
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-soft">
              聚合 1-5 个产品的评论自由提问，并返回引用评论，适合做竞品分析、选品判断和运营巡检。
            </p>
            <Link
              href="/pricing"
              className="mt-6 inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
            >
              查看升级方案
            </Link>
          </section>
        </AppShell>
      );
    }

    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/qa"
          title="Ask Reviews 需要先登录。"
          description="登录后会直接读取当前账号的产品评论资产。"
        >
          <EmptyAuthState
            title="登录后查看 Ask Reviews"
            description="这条能力会使用当前账号的产品评论范围，并返回带证据的回答。"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
