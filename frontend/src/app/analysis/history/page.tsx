import Link from "next/link";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { DeleteSessionButton } from "@/components/analysis/delete-session-button";
import { getAnalysisHistory, getAnalysisSessionHistory, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Analysis History | ClueAI",
  description: "Authenticated history of uploaded review batches.",
});

type HistoryPageProps = {
  searchParams?: Promise<{
    product_id?: string;
    session_id?: string;
  }>;
};

export default async function AnalysisHistoryPage({
  searchParams,
}: HistoryPageProps) {
  try {
    const params = searchParams ? await searchParams : undefined;
    const productId = params?.product_id?.trim();
    const selectedSessionId = params?.session_id ? Number(params.session_id) : undefined;
    const payload =
      selectedSessionId && Number.isFinite(selectedSessionId)
        ? await getAnalysisSessionHistory(selectedSessionId)
        : await getAnalysisHistory(productId);

    return (
      <AppShell
        currentPath="/analysis/history"
        title="历史页按产品组汇总所有分析批次。"
        description="这里不再依赖页面内部状态，直接从后端读取历史批次，方便从任意 URL 直达。"
      >
        <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
            HISTORY
          </div>
          <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
            {payload.total} 个分析批次
          </h2>
          <p className="mt-3 text-sm leading-7 text-soft">
            历史页可以作为结果页和对比页的入口，先从产品组列表里挑一个批次。
          </p>
        </section>

        {payload.selected_session_id ? (
          <section className="rounded-shell border border-line bg-[#f8fffc] px-6 py-4 text-sm leading-7 text-soft">
            当前聚焦批次 ID: {payload.selected_session_id}
            {payload.selected_product_id ? ` · 产品 ${payload.selected_product_id}` : ""}
          </section>
        ) : null}

        <section className="space-y-6">
          {payload.items.map((group) => (
            <article key={group.product_id} className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
              <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
                {group.product_id}
              </h3>
              <div className="mt-4 grid gap-3">
                {group.sessions.map((session) => (
                  <div key={session.id} className="rounded-card border border-line bg-white px-4 py-4">
                    <div className="text-sm font-semibold text-ink">{session.title}</div>
                    <div className="mt-2 text-sm leading-7 text-soft">
                      {session.version} · {session.created_at} · {session.total_reviews} 条评论
                    </div>
                    <div className="mt-4 flex flex-wrap gap-3">
                      <Link
                        href={`/analysis/results?session_id=${session.id}`}
                        className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
                      >
                        看结果
                      </Link>
                      <Link
                        href={`/analysis/compare?product_id=${encodeURIComponent(session.product_id)}&session_id=${session.id}`}
                        className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-ink"
                      >
                        去对比
                      </Link>
                      <DeleteSessionButton
                        sessionId={session.id}
                        sessionTitle={session.title}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
          {payload.items.length === 0 ? (
            <div className="rounded-shell border border-dashed border-line bg-[#fffafb] px-5 py-6 text-sm leading-7 text-soft">
              当前没有历史分析批次。
            </div>
          ) : null}
        </section>
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/analysis/history"
          title="分析历史需要先登录。"
          description="登录后可以直接查看当前账号下的所有分析批次。"
        >
          <EmptyAuthState
            title="登录后查看分析历史"
            description="这里会按产品组汇总你上传过的所有分析批次，方便跳转结果页或对比页。"
          />
        </AppShell>
      );
    }

    throw error;
  }
}
