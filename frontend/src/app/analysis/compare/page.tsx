import Link from "next/link";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { CompareWorkspace } from "@/components/analysis/compare-workspace";
import { getProducts, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Compare Analysis | ClueAI",
  description: "Authenticated compare view for products, batches, and versions.",
});

type ComparePageProps = {
  searchParams?: Promise<{
    product_id?: string;
    compare_type?: string;
  }>;
};

const ALLOWED_MODES = new Set([
  "same_product_time",
  "same_product_version",
  "multi_product",
]);

export default async function AnalysisComparePage({ searchParams }: ComparePageProps) {
  try {
    const params = searchParams ? await searchParams : undefined;
    const productId = params?.product_id?.trim();
    const compareTypeParam = params?.compare_type?.trim();
    const compareType =
      compareTypeParam && ALLOWED_MODES.has(compareTypeParam)
        ? (compareTypeParam as "same_product_time" | "same_product_version" | "multi_product")
        : "same_product_time";

    const productsResponse = await getProducts();

    return (
      <AppShell
        currentPath="/analysis/compare"
        title="对比分析"
        description="按产品、版本和评论时间窗口筛选，对比核心指标、TOP 问题 / 亮点，下载 XLSX 报表。"
      >
        <div className="flex gap-2">
          <Link
            href="/analysis/history"
            className="inline-flex min-h-9 items-center justify-center rounded-pill border border-line bg-white px-4 py-2 text-sm font-semibold text-ink"
          >
            去历史记录挑批次
          </Link>
        </div>
        <CompareWorkspace
          products={productsResponse.items}
          initialMode={compareType}
          initialProductId={productId}
        />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/analysis/compare"
          title="对比分析需要先登录。"
          description="登录后可以按产品、批次和版本进行多维对比。"
        >
          <EmptyAuthState
            title="登录后查看对比分析"
            description="这里支持同一产品不同时间、多版本对比和跨产品对比，先登录再开始。"
          />
        </AppShell>
      );
    }

    return (
      <AppShell
        currentPath="/analysis/compare"
        title="对比分析暂时无法加载。"
        description="数据加载失败，可能是分析批次不足或服务暂时不可用。"
      >
        <section className="rounded-shell border border-dashed border-line bg-[#fffafb] px-6 py-10 shadow-card backdrop-blur">
          <h2 className="font-heading text-xl font-extrabold tracking-[-0.04em] text-ink">
            暂无可用对比数据
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-soft">
            对比分析需要至少两个分析批次。请先上传评论完成分析，再回到这里选择对比对象。
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href="/analysis/history"
              className="inline-flex min-h-9 items-center justify-center rounded-pill bg-ink px-5 py-2 text-sm font-semibold text-white shadow-card"
            >
              去历史记录
            </Link>
            <Link
              href="/upload"
              className="inline-flex min-h-9 items-center justify-center rounded-pill border border-line bg-white px-5 py-2 text-sm font-semibold text-ink"
            >
              上传评论
            </Link>
          </div>
        </section>
      </AppShell>
    );
  }
}
