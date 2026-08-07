"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  PageTabs,
  PageTabsList,
  PageTabsTrigger,
  PageTabsContent,
} from "@/components/ui/page-tabs";
import GoldenSetTab from "@/components/label-calibration/golden-set-tab";
import RegistryReviewTab from "@/components/label-calibration/registry-review-tab";

export default function GoldenSetPage() {
  const t = useTranslations("settings.goldenSet");
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    fetch("/api/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d?.is_admin) {
          setAuthorized(true);
        } else {
          router.replace("/workspace");
        }
      })
      .catch(() => router.replace("/workspace"));
  }, [router]);

  if (!authorized) return null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-bold text-ink">{t("pageTitle")}</h1>

      <PageTabs defaultValue="calibration" className="mt-6">
        <PageTabsList>
          <PageTabsTrigger value="calibration">{t("title")}</PageTabsTrigger>
          <PageTabsTrigger value="registry-review">{t("tabRegistryReview")}</PageTabsTrigger>
        </PageTabsList>

        <PageTabsContent value="calibration">
          <GoldenSetTab />
        </PageTabsContent>
        <PageTabsContent value="registry-review">
          <RegistryReviewTab />
        </PageTabsContent>
      </PageTabs>
    </div>
  );
}
