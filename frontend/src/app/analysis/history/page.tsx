import Link from "next/link";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { DeleteSessionButton } from "@/components/analysis/delete-session-button";
import { getAnalysisHistory, getAnalysisSessionHistory, isApiError } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
        title="分析历史"
        description={`共 ${payload.total} 个分析批次，按产品分组`}
      >
        {payload.selected_session_id ? (
          <section className="rounded-card border border-line bg-[#f8fffc] px-5 py-3 text-sm text-soft">
            当前聚焦批次 ID: {payload.selected_session_id}
            {payload.selected_product_id ? ` · 产品 ${payload.selected_product_id}` : ""}
          </section>
        ) : null}

        <section className="space-y-4">
          {payload.items.map((group) => (
            <article key={group.product_id} className="rounded-shell border border-line bg-white/84 p-5 shadow-card backdrop-blur">
              <h3 className="font-heading text-lg font-extrabold tracking-[-0.04em] text-ink">
                {group.product_id}
              </h3>
              <Table className="mt-3">
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>批次标题</TableHead>
                    <TableHead className="w-20">版本</TableHead>
                    <TableHead className="w-28">时间</TableHead>
                    <TableHead className="w-16">评论</TableHead>
                    <TableHead className="w-48">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {group.sessions.map((session) => (
                    <TableRow key={session.id}>
                      <TableCell className="text-sm font-semibold text-ink">{session.title}</TableCell>
                      <TableCell className="text-sm text-soft">{session.version}</TableCell>
                      <TableCell className="text-xs text-soft">{session.created_at}</TableCell>
                      <TableCell className="text-sm text-soft">{session.total_reviews}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Link
                            href={`/analysis/results?session_id=${session.id}`}
                            className="inline-flex items-center rounded-pill bg-ink px-3 py-1.5 text-xs font-semibold text-white"
                          >
                            看结果
                          </Link>
                          <Link
                            href={`/analysis/compare?product_id=${encodeURIComponent(session.product_id)}&session_id=${session.id}`}
                            className="inline-flex items-center rounded-pill border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink"
                          >
                            对比
                          </Link>
                          <DeleteSessionButton
                            sessionId={session.id}
                            sessionTitle={session.title}
                          />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </article>
          ))}
          {payload.items.length === 0 ? (
            <div className="rounded-shell border border-dashed border-line bg-[#fffafb] px-5 py-5 text-sm text-soft">
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
