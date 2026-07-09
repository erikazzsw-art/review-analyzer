"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  PageTabs,
  PageTabsList,
  PageTabsTrigger,
  PageTabsContent,
} from "@/components/ui/page-tabs";
import { TimeRangeSelect } from "@/components/observability/time-range-select";
import { ModelStatusRow } from "@/components/observability/model-status-row";
import { OverviewTab } from "@/components/observability/overview-tab";
import { CostTab } from "@/components/observability/cost-tab";
import { JobsTab } from "@/components/observability/jobs-tab";
import { CacheTab } from "@/components/observability/cache-tab";
import { AlertsTab } from "@/components/observability/alerts-tab";
import type { TimeRange } from "@/components/observability/types";

export default function ObservabilityPage() {
  const t = useTranslations("settings.observability");
  const [timeRange, setTimeRange] = useState<TimeRange>("7d");

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-ink">{t("title")}</h1>
        <TimeRangeSelect value={timeRange} onChange={setTimeRange} />
      </div>

      <div className="mt-4">
        <ModelStatusRow />
      </div>

      <PageTabs defaultValue="overview" className="mt-6">
        <PageTabsList>
          <PageTabsTrigger value="overview">{t("tabOverview")}</PageTabsTrigger>
          <PageTabsTrigger value="cost">{t("tabCost")}</PageTabsTrigger>
          <PageTabsTrigger value="jobs">{t("tabJobs")}</PageTabsTrigger>
          <PageTabsTrigger value="cache">{t("tabCache")}</PageTabsTrigger>
          <PageTabsTrigger value="alerts">{t("tabAlerts")}</PageTabsTrigger>
        </PageTabsList>

        <PageTabsContent value="overview">
          <OverviewTab timeRange={timeRange} />
        </PageTabsContent>
        <PageTabsContent value="cost">
          <CostTab timeRange={timeRange} />
        </PageTabsContent>
        <PageTabsContent value="jobs">
          <JobsTab />
        </PageTabsContent>
        <PageTabsContent value="cache">
          <CacheTab timeRange={timeRange} />
        </PageTabsContent>
        <PageTabsContent value="alerts">
          <AlertsTab />
        </PageTabsContent>
      </PageTabs>
    </div>
  );
}
