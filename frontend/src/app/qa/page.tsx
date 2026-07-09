import Link from "next/link";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { QaPanel } from "@/components/analysis/qa-panel";
import { getQaProducts, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Review Q&A",
  description: "Authenticated question answering over review evidence.",
});

export default async function QaPage() {
  try {
    const products = await getQaProducts();
    return (
      <AppShell
        currentPath="/qa"
        title="问评论"
        description="选择产品，围绕评论自由提问，支持多轮追问。"
      >
        <QaPanel products={products} />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 403) {
      return (
        <AppShell
          currentPath="/qa"
          title="问评论需要 Pro 权限。"
          description="这条能力保留在高级入口里，升级后就能按产品聚合评论并继续追问。"
        >
          <section className="rounded-shell border border-dashed border-line bg-white/80 px-6 py-10 shadow-card backdrop-blur">
            <div className="inline-flex rounded-pill bg-[#fff1f5] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
              PRO FEATURE
            </div>
            <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
              升级后解锁问评论
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-soft">
              这一步可以把 1-5 个产品的评论聚合起来提问，并返回引用评论，适合做更深入的运营追问。
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
          title="问评论需要先登录。"
          description="登录后会直接读取当前账号的产品评论资产。"
        >
          <EmptyAuthState
            title="登录后查看问评论"
            description="这条能力会使用当前账号的产品评论范围，并返回带证据的回答。"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
