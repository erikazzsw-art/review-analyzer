import Link from "next/link";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { CompareReportPanel } from "@/components/analysis/compare-report-panel";
import { getAnalysisCompare, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";
import type { AnalysisCompareGroup } from "@/lib/api/types";

export const metadata = buildNoIndexMetadata({
  title: "Compare Analysis | ClueAI",
  description: "Authenticated compare view for products, batches, and versions.",
});

type ComparePageProps = {
  searchParams?: Promise<{
    product_id?: string;
    session_id?: string | string[];
    compare_type?: string;
  }>;
};

const compareTypeLabels: Record<string, string> = {
  same_product_time: "同一产品不同时间维度",
  same_product_version: "同一产品多版本对比",
  multi_product: "跨产品对比",
  custom: "自定义对比",
};

function renderCompareGroupMeta(group: AnalysisCompareGroup): string {
  const meta = [
    group.product_id,
    group.versions.length > 0 ? `版本 ${group.versions.join(" / ")}` : "",
    group.session_ids.length > 0 ? `批次 ${group.session_ids.join(" / ")}` : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return meta || "未设置筛选元数据";
}

export default async function AnalysisComparePage({
  searchParams,
}: ComparePageProps) {
  try {
  const params = searchParams ? await searchParams : undefined;
  const productId = params?.product_id?.trim();
  const compareType = params?.compare_type?.trim() || "custom";
  const sessionIds = params?.session_id
    ? Array.isArray(params.session_id)
      ? params.session_id.map((value) => Number(value)).filter(Number.isFinite)
      : [Number(params.session_id)].filter(Number.isFinite)
    : undefined;
  const payload = await getAnalysisCompare({ compareType, productId, sessionIds });
  const reportSessionIds = payload.groups.flatMap((group) => group.session_ids);

  return (
    <AppShell
      currentPath="/analysis/compare"
      title="对比页现在可以按产品、批次和对比类型直达。"
      description="这里补上筛选入口后，就能直接切换时间、版本或多产品对比，不必先回历史页重选。"
    >
      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
          COMPARE
        </div>
        <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          {compareTypeLabels[payload.compare_type] || payload.compare_type}
        </h2>
        <p className="mt-3 text-sm leading-7 text-soft">
          当前已读取 {payload.groups.length} 个对比对象。你可以直接用下面的筛选条切换类型、产品和批次。
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href="/analysis/history"
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
          >
            去历史记录挑批次
          </Link>
          <Link
            href={`/analysis/compare?compare_type=${compareType}&${productId ? `product_id=${encodeURIComponent(productId)}&` : ""}${sessionIds?.map((value) => `session_id=${value}`).join("&") || ""}`}
            className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-ink"
          >
            刷新当前筛选
          </Link>
        </div>
      </section>

      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="grid gap-4 lg:grid-cols-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">对比类型</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {Object.entries(compareTypeLabels).map(([key, label]) => (
                <Link
                  key={key}
                  href={`/analysis/compare?compare_type=${key}${productId ? `&product_id=${encodeURIComponent(productId)}` : ""}${sessionIds?.length ? `&${sessionIds.map((value) => `session_id=${value}`).join("&")}` : ""}`}
                  className={[
                    "rounded-pill border px-4 py-2 text-sm font-semibold transition",
                    payload.compare_type === key
                      ? "border-transparent bg-ink text-white shadow-card"
                      : "border-line bg-white text-soft hover:text-ink",
                  ].join(" ")}
                >
                  {label}
                </Link>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">当前产品</div>
            <div className="mt-3 text-sm leading-7 text-ink">
              {productId ? productId : "未指定产品，将从历史中自动选取候选对象"}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">当前批次</div>
            <div className="mt-3 text-sm leading-7 text-ink">
              {sessionIds && sessionIds.length > 0
                ? sessionIds.join(" / ")
                : "未指定批次，系统会使用当前产品下的默认批次"}
            </div>
          </div>
        </div>
      </section>

      <CompareReportPanel
        compareType={payload.compare_type}
        sessionIds={reportSessionIds}
        productId={productId}
      />

      <section className="space-y-5">
        <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            对比矩阵
          </h3>
          <p className="mt-2 text-sm leading-7 text-soft">
            先看整体摘要，再往下看各维度的差异和代表性评论。
          </p>
        </div>
        {payload.comparison_rows.map((row, index) => (
          <div key={`compare-row-${index}`} className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {Object.entries(row).map(([key, value]) => (
                <div key={key} className="rounded-card border border-line bg-white px-4 py-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                    {key}
                  </div>
                  <div className="mt-2 text-sm leading-7 text-ink">
                    {String(value)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
        {payload.comparison_rows.length === 0 ? (
          <div className="rounded-shell border border-dashed border-line bg-[#fffafb] px-5 py-6 text-sm leading-7 text-soft">
            当前没有足够的对比对象。可以先上传同一产品的两个批次，再回来查看。
          </div>
        ) : null}
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            推荐动作
          </h3>
          <div className="mt-4 space-y-3">
            {payload.recommended_actions.map((item, index) => (
              <div key={`action-${index}`} className="rounded-card border border-line bg-white px-4 py-4 text-sm leading-7 text-ink">
                {item}
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            空结果提示
          </h3>
          <div className="mt-4 space-y-3">
            {payload.empty_groups.length > 0 ? (
              payload.empty_groups.map((item, index) => (
                <div key={`empty-${index}`} className="rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
                  {item}
                </div>
              ))
            ) : (
              <div className="rounded-card border border-line bg-[#f8fffc] px-4 py-4 text-sm leading-7 text-soft">
                暂时没有空组，说明这批对比对象都找到了可用评论。
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            差异标签
          </h3>
          <div className="mt-4 space-y-3">
            {payload.issue_differences.length > 0 ? (
              payload.issue_differences.slice(0, 8).map((item, index) => (
                <div key={`issue-diff-${index}`} className="rounded-card border border-line bg-white px-4 py-4 text-sm leading-7 text-ink">
                  {Object.entries(item).map(([key, value]) => (
                    <div key={key} className="flex justify-between gap-3">
                      <span className="font-semibold text-soft">{key}</span>
                      <span className="text-right">{String(value)}</span>
                    </div>
                  ))}
                </div>
              ))
            ) : (
              <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
                暂时没有足够的标签差异，通常意味着批次还太少或表现比较接近。
              </div>
            )}
          </div>
        </div>
        <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            亮点差异
          </h3>
          <div className="mt-4 space-y-3">
            {payload.highlight_differences.length > 0 ? (
              payload.highlight_differences.slice(0, 8).map((item, index) => (
                <div key={`highlight-diff-${index}`} className="rounded-card border border-line bg-white px-4 py-4 text-sm leading-7 text-ink">
                  {Object.entries(item).map(([key, value]) => (
                    <div key={key} className="flex justify-between gap-3">
                      <span className="font-semibold text-soft">{key}</span>
                      <span className="text-right">{String(value)}</span>
                    </div>
                  ))}
                </div>
              ))
            ) : (
              <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
                暂时没有足够的亮点差异。
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            风险对象
          </h3>
          <div className="mt-4 space-y-3">
            {payload.risk_groups.length > 0 ? (
              payload.risk_groups.map((item, index) => (
                <div key={`risk-${index}`} className="rounded-card border border-line bg-[#fff8f9] px-4 py-4 text-sm leading-7 text-ink">
                  <div className="font-semibold">{renderCompareGroupMeta(item as AnalysisCompareGroup)}</div>
                  <div className="mt-2 text-soft">
                    差评率 {String(item.negative_rate)}% · {String(item.review_count)} 条评论 · TOP 问题 {String(item.top_issue)}
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
                当前没有明显的风险对象。
              </div>
            )}
          </div>
        </div>
        <div className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            机会对象
          </h3>
          <div className="mt-4 space-y-3">
            {payload.opportunity_groups.length > 0 ? (
              payload.opportunity_groups.map((item, index) => (
                <div key={`opportunity-${index}`} className="rounded-card border border-line bg-[#f8fffc] px-4 py-4 text-sm leading-7 text-ink">
                  <div className="font-semibold">{renderCompareGroupMeta(item as AnalysisCompareGroup)}</div>
                  <div className="mt-2 text-soft">
                    好评率 {String(item.positive_rate)}% · {String(item.review_count)} 条评论 · TOP 亮点 {String(item.top_highlight)}
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-4 py-4 text-sm leading-7 text-soft">
                当前没有明显的机会对象。
              </div>
            )}
          </div>
        </div>
      </section>
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
          <h2 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
            暂无可用对比数据
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-soft">
            对比分析需要至少两个分析批次。请先上传评论完成分析，再回到这里选择对比对象。
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/analysis/history"
              className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
            >
              去历史记录
            </Link>
            <Link
              href="/upload"
              className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-ink"
            >
              上传评论
            </Link>
          </div>
        </section>
      </AppShell>
    );
  }
}
