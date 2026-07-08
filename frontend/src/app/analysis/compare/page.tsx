import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { AppShell } from "@/components/app/app-shell";
import { EmptyAuthState } from "@/components/app/empty-auth-state";
import { CompareWorkspace } from "@/components/analysis/compare-workspace";
import { getCompareLatest, getProducts, isApiError } from "@/lib/api/server";
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
  const t = await getTranslations("analysis.compare");
  try {
    const params = searchParams ? await searchParams : undefined;
    const productId = params?.product_id?.trim();
    const compareTypeParam = params?.compare_type?.trim();
    const compareType =
      compareTypeParam && ALLOWED_MODES.has(compareTypeParam)
        ? (compareTypeParam as "same_product_time" | "same_product_version" | "multi_product")
        : undefined;

    const [productsResponse, latestResponse] = await Promise.all([
      getProducts(),
      getCompareLatest(),
    ]);

    const initialMode = compareType ?? (latestResponse?.compare_type as "same_product_time" | "same_product_version" | "multi_product" | undefined) ?? "same_product_time";
    const initialDataset = latestResponse?.dataset ?? null;
    const initialGroups = latestResponse?.filter_groups
      ? (latestResponse.filter_groups as Array<Record<string, unknown>>).map((g) => ({
          productId: (g.productId ?? g.product_id ?? "") as string,
          versions: (g.versions ?? []) as string[],
          dateStart: (g.dateStart ?? g.date_start ?? undefined) as string | undefined,
          dateEnd: (g.dateEnd ?? g.date_end ?? undefined) as string | undefined,
        }))
      : undefined;

    return (
      <AppShell
        currentPath="/analysis/compare"
        title={t("pageTitle")}
        description={t("pageDescription")}
      >
        <div className="flex gap-2">
          <Link
            href="/analysis/history"
            className="inline-flex min-h-9 items-center justify-center rounded-pill border border-line bg-white px-4 py-2 text-sm font-semibold text-ink"
          >
            {t("goHistoryPick")}
          </Link>
        </div>
        <CompareWorkspace
          products={productsResponse.items}
          initialMode={initialMode}
          initialProductId={productId}
          initialDataset={initialDataset}
          initialGroups={initialGroups}
        />
      </AppShell>
    );
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      return (
        <AppShell
          currentPath="/analysis/compare"
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

    return (
      <AppShell
        currentPath="/analysis/compare"
        title={t("loadFailedTitle")}
        description={t("loadFailedSubtitle")}
      >
        <section className="rounded-shell border border-dashed border-line bg-[#fffafb] px-6 py-10 shadow-card backdrop-blur">
          <h2 className="font-heading text-xl font-extrabold tracking-[-0.04em] text-ink">
            {t("emptyTitle")}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-soft">
            {t("emptyDesc")}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href="/analysis/history"
              className="inline-flex min-h-9 items-center justify-center rounded-pill bg-ink px-5 py-2 text-sm font-semibold text-white shadow-card"
            >
              {t("goHistory")}
            </Link>
            <Link
              href="/upload"
              className="inline-flex min-h-9 items-center justify-center rounded-pill border border-line bg-white px-5 py-2 text-sm font-semibold text-ink"
            >
              {t("goUpload")}
            </Link>
          </div>
        </section>
      </AppShell>
    );
  }
}
