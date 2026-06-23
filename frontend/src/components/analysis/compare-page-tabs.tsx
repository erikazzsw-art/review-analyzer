"use client";

import type { ReactNode } from "react";
import {
  PageTabs,
  PageTabsList,
  PageTabsTrigger,
  PageTabsContent,
} from "@/components/ui/page-tabs";

type Props = {
  filterSlot: ReactNode;
  matrixSlot: ReactNode;
  differencesSlot: ReactNode;
  riskSlot: ReactNode;
  actionsSlot: ReactNode;
};

export function ComparePageTabs({
  filterSlot,
  matrixSlot,
  differencesSlot,
  riskSlot,
  actionsSlot,
}: Props) {
  return (
    <PageTabs defaultValue="matrix">
      <div className="rounded-shell border border-line bg-white shadow-card">
        <PageTabsList>
          <PageTabsTrigger value="matrix">筛选 & 矩阵</PageTabsTrigger>
          <PageTabsTrigger value="differences">差异分析</PageTabsTrigger>
          <PageTabsTrigger value="risk">风险 & 机会</PageTabsTrigger>
          <PageTabsTrigger value="actions">推荐动作</PageTabsTrigger>
        </PageTabsList>
      </div>

      <PageTabsContent value="matrix">
        <div className="flex flex-col gap-4">
          {filterSlot}
          {matrixSlot}
        </div>
      </PageTabsContent>

      <PageTabsContent value="differences">
        {differencesSlot}
      </PageTabsContent>

      <PageTabsContent value="risk">
        {riskSlot}
      </PageTabsContent>

      <PageTabsContent value="actions">
        {actionsSlot}
      </PageTabsContent>
    </PageTabs>
  );
}
