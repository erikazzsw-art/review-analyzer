"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense } from "react";

import { MarketingShell } from "@/components/marketing/marketing-shell";

// 三种状态由 backend GET /api/unsubscribe 302 时的 ?status 参数决定:
//   success — DB 更新成功
//   pending — DB 更新失败(通常是 marketing_opt_in 字段未上线,041 前预期路径)
//   error   — token 无效或 user 不存在
type Status = "success" | "pending" | "error";

function isStatus(value: string | null): value is Status {
  return value === "success" || value === "pending" || value === "error";
}

function UnsubscribedContent() {
  const t = useTranslations("unsubscribed");
  const params = useSearchParams();
  const raw = params.get("status");
  const status: Status = isStatus(raw) ? raw : "success";

  return (
    <MarketingShell
      title={t(`${status}.title`)}
      description={t(`${status}.description`)}
    >
      <div className="mx-auto max-w-2xl px-4 py-8 text-center">
        <p className="text-base leading-7 text-soft">{t(`${status}.body`)}</p>
        <div className="mt-8 flex flex-col items-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center rounded-lg bg-ink px-6 py-2.5 text-sm font-semibold text-white transition hover:opacity-90"
          >
            {t("backHome")}
          </Link>
          {status !== "success" ? (
            <p className="text-xs text-muted-foreground">
              {t.rich("contactSupport", {
                mail: (chunks) => (
                  <a
                    href="mailto:support@clueai-reviewlens.com"
                    className="underline"
                  >
                    {chunks}
                  </a>
                ),
              })}
            </p>
          ) : null}
        </div>
      </div>
    </MarketingShell>
  );
}

export default function UnsubscribedPage() {
  // useSearchParams 需要 Suspense 边界(Next 15 静态渲染要求)
  return (
    <Suspense fallback={null}>
      <UnsubscribedContent />
    </Suspense>
  );
}
