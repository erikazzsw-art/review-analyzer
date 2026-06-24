import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { CopywriterWorkspace } from "@/components/copywriter/copywriter-workspace";
import { getCopywriterPlatforms, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Marketing Copy | ClueAI",
  description: "Authenticated copy generation for products and campaigns.",
});

type SearchParams = {
  product_id?: string;
  version?: string;
  range?: string;
  platform?: string;
  style?: string;
};

export default async function CopywriterPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  try {
    // 仅用作 Pro / 鉴权探针；workspace 自己拉一次最新平台与风格
    await getCopywriterPlatforms();
    const params = await searchParams;
    return (
      <AppShell
        currentPath="/copywriter"
        title="把评论洞察转成可直接使用的广告文案。"
        description="选择产品和版本后，系统按平台规则生成英文文案与中文参考，并同步出一份理想产品画像。"
      >
        <CopywriterWorkspace
          productId={params.product_id ?? ""}
          version={params.version ?? ""}
          range={params.range ?? "all"}
          platform={params.platform ?? "amazon"}
          style={params.style ?? "简洁专业"}
        />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/copywriter"
          title="宣传文案需要先登录。"
          description="登录后会直接读取当前账号的产品与评论资产。"
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
