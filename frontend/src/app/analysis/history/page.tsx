import Link from "next/link";
import { getTranslations } from "next-intl/server";

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
  const t = await getTranslations("analysis.history");
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
        title={t("title")}
        description={t("totalFormat", { total: payload.total })}
      >
        {payload.selected_session_id ? (
          <section className="rounded-card border border-line bg-[#f8fffc] px-5 py-3 text-sm text-soft">
            {t("currentFocus", { sessionId: payload.selected_session_id })}
            {payload.selected_product_id
              ? t("currentFocusProduct", { productId: payload.selected_product_id })
              : ""}
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
                    <TableHead>{t("headBatchTitle")}</TableHead>
                    <TableHead className="w-20">{t("headVersion")}</TableHead>
                    <TableHead className="w-28">{t("headTime")}</TableHead>
                    <TableHead className="w-16">{t("headReviews")}</TableHead>
                    <TableHead className="w-48">{t("headActions")}</TableHead>
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
                            {t("viewResults")}
                          </Link>
                          <Link
                            href={`/analysis/compare?product_id=${encodeURIComponent(session.product_id)}&session_id=${session.id}`}
                            className="inline-flex items-center rounded-pill border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink"
                          >
                            {t("compareLink")}
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
              {t("empty")}
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
          title={t("loginTitle")}
          description={t("loginSubtitle")}
        >
          <EmptyAuthState
            title={t("loginEmptyTitle")}
            description={t("loginEmptyDesc")}
          />
        </AppShell>
      );
    }

    throw error;
  }
}
