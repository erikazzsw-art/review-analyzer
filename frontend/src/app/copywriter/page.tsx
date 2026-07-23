import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { CopywriterWorkspace } from "@/components/copywriter/copywriter-workspace";
import { getCopywriterPlatforms, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Listing Copy",
  description: "Authenticated listing and campaign copy generation from review insights.",
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
        title="把评论洞察转成 Listing 和广告文案。"
        description="选择产品和版本后，系统按平台规则生成英文文案、中文参考和理想产品画像。"
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
          title="Listing 文案需要先登录。"
          description="登录后会直接读取当前账号的产品与评论资产。"
        >
          <EmptyAuthState
            title="登录后生成 Listing 文案"
            description="这里会把评论洞察、平台规则和产品卖点整理成可直接测试的文案。"
          />
        </AppShell>
      );
    }

    if (isApiError(error) && error.status === 403) {
      return (
        <AppShell
          currentPath="/copywriter"
          title="Listing 文案是 Pro 功能。"
          description="这条能力适合在发现痛点、亮点和竞品机会后，继续扩大到 Listing 与广告优化。"
        >
          <section className="rounded-shell border border-dashed border-line bg-white/80 px-6 py-10 shadow-card backdrop-blur">
            <div className="inline-flex rounded-pill bg-[#fff1f5] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
              PRO FEATURE
            </div>
            <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
              升级后解锁 Listing 文案
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
