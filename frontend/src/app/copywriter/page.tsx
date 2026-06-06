import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { CopywriterPanel } from "@/components/copywriter/copywriter-panel";
import { getCopywriterSessions, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Marketing Copy | ClueAI",
  description: "Authenticated copy generation for products and campaigns.",
});

export default async function CopywriterPage() {
  try {
    const sessions = await getCopywriterSessions();
    return (
      <AppShell
        currentPath="/copywriter"
        title="把评论洞察转成可直接使用的广告文案。"
        description="这一页承接分析批次，按平台生成文案和理想产品画像。它是高价值但低频的输出入口，所以放在独立页面里。"
      >
        <CopywriterPanel sessions={sessions} />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/copywriter"
          title="宣传文案需要先登录。"
          description="登录后会直接读取当前账号的分析批次和评论资产。"
        >
          <EmptyAuthState
            title="登录后生成宣传文案"
            description="这里会把评论摘要、平台规则和产品功能点一起整理成可用文案。"
          />
        </AppShell>
      );
    }

    if (isApiError(error) && error.status === 403) {
      return (
        <AppShell
          currentPath="/copywriter"
          title="宣传文案是 Pro 功能。"
          description="这条能力保留在升级后入口里，适合已经看到价值后继续扩大使用。"
        >
          <section className="rounded-shell border border-dashed border-line bg-white/80 px-6 py-10 shadow-card backdrop-blur">
            <div className="inline-flex rounded-pill bg-[#fff1f5] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
              PRO FEATURE
            </div>
            <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
              升级后解锁宣传文案
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-soft">
              这一步可以把评论洞察转换成按平台可直接使用的广告文案、卖点表达和客户画像。
            </p>
          </section>
        </AppShell>
      );
    }

    throw error;
  }
}
