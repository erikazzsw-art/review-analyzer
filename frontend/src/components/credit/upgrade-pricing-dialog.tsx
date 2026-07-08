"use client";

import Link from "next/link";
import { Fragment, useRef, useState } from "react";
import { Check, Minus } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { createBillingCheckout } from "@/lib/api/browser";
import {
  PLANS,
  type BillingPeriod,
  type PlanKey,
  type PlanPricing,
} from "@/lib/pricing";

type UpgradePricingDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentPlan: PlanKey;
  onOpenLedger: () => void;
};

const PLAN_ORDER: PlanKey[] = ["free", "starter", "pro", "team"];

const PLAN_NAME_CN: Record<PlanKey, string> = {
  free: "免费版",
  starter: "入门版",
  pro: "专业版",
  team: "团队版",
};

const PLAN_HIGHLIGHTS: Record<PlanKey, string[]> = {
  free: [
    "300 credits / 月",
    "1 个产品组",
    "单次上传 500 条评论",
    "情感分析 + 标签",
    "社区支持",
  ],
  starter: [
    "5,000 credits / 月",
    "3 个产品组",
    "单次上传 1,000 条评论",
    "Ask Reviews 智能问答",
    "广告文案生成",
    "邮件支持",
  ],
  pro: [
    "15,000 credits / 月",
    "不限产品组",
    "单次上传 5,000 条评论",
    "多产品对比",
    "Webhook 集成",
    "优先支持",
  ],
  team: [
    "45,000 credits / 月",
    "包含专业版全部功能",
    "多成员协作",
    "角色权限管理",
    "SLA 保障",
    "专属客户经理",
  ],
};

type CellValue = string | boolean;

type ComparisonRow = {
  label: string;
  values: Record<PlanKey, CellValue>;
};

type ComparisonGroup = {
  title: string;
  rows: ComparisonRow[];
};

const COMPARISON_GROUPS: ComparisonGroup[] = [
  {
    title: "积分与配额",
    rows: [
      {
        label: "月度 Credits",
        values: { free: "300", starter: "5,000", pro: "15,000", team: "45,000" },
      },
      {
        label: "单次上传上限",
        values: { free: "500 条", starter: "1,000 条", pro: "5,000 条", team: "5,000 条" },
      },
      {
        label: "ASIN 自动拉取",
        values: { free: "1 次/天", starter: "10 次/天", pro: "10 次/天", team: "50 次/天" },
      },
    ],
  },
  {
    title: "评论分析",
    rows: [
      {
        label: "情感分析与标签",
        values: { free: true, starter: true, pro: true, team: true },
      },
      {
        label: "Ask Reviews 问答",
        values: { free: true, starter: true, pro: true, team: true },
      },
      {
        label: "Insight 深度报告",
        values: { free: true, starter: true, pro: true, team: true },
      },
      {
        label: "多产品对比",
        values: { free: "2 款", starter: "不限", pro: "不限", team: "不限" },
      },
    ],
  },
  {
    title: "内容生成",
    rows: [
      {
        label: "广告文案",
        values: { free: true, starter: true, pro: true, team: true },
      },
      {
        label: "翻译",
        values: { free: "20 次/天", starter: "200 次/天", pro: "200 次/天", team: "500 次/天" },
      },
    ],
  },
  {
    title: "导出与集成",
    rows: [
      {
        label: "Excel/CSV 导出",
        values: { free: "10 次/月", starter: "不限", pro: "不限", team: "不限" },
      },
      {
        label: "Webhook 集成",
        values: { free: "3 个", starter: "不限", pro: "不限", team: "不限" },
      },
      {
        label: "预警规则",
        values: { free: "全局 3 条", starter: "不限", pro: "不限", team: "不限" },
      },
      {
        label: "API 密钥",
        values: { free: false, starter: false, pro: "3 个（即将）", team: "10 个（即将）" },
      },
    ],
  },
  {
    title: "团队与支持",
    rows: [
      {
        label: "多成员协作",
        values: { free: false, starter: false, pro: false, team: true },
      },
      {
        label: "角色权限",
        values: { free: false, starter: false, pro: false, team: true },
      },
      {
        label: "客服支持",
        values: { free: "社区", starter: "邮件", pro: "优先", team: "专属经理" },
      },
    ],
  },
];

function priceLabel(plan: PlanPricing, period: BillingPeriod): string {
  if (plan.monthlyUsd === 0) return "$0";
  const value = period === "annual" ? plan.annualMonthlyUsd : plan.monthlyUsd;
  return `$${value % 1 === 0 ? value : value.toFixed(1)}`;
}

export function UpgradePricingDialog({
  open,
  onOpenChange,
  currentPlan,
  onOpenLedger,
}: UpgradePricingDialogProps) {
  const [billingCycle, setBillingCycle] = useState<BillingPeriod>("monthly");
  const [checkoutLoading, setCheckoutLoading] = useState<PlanKey | null>(null);
  const [error, setError] = useState<string>("");
  const checkoutRef = useRef<HTMLDivElement | null>(null);

  async function handlePaidCheckout(planKey: PlanKey) {
    setError("");
    setCheckoutLoading(planKey);
    try {
      const result = await createBillingCheckout();
      if (!result.checkout_html) {
        onOpenChange(false);
        return;
      }
      if (checkoutRef.current) {
        checkoutRef.current.innerHTML = result.checkout_html;
        const scripts = Array.from(checkoutRef.current.querySelectorAll("script"));
        for (const script of scripts) {
          await new Promise<void>((resolve, reject) => {
            const next = document.createElement("script");
            Array.from(script.attributes).forEach((attr) =>
              next.setAttribute(attr.name, attr.value),
            );
            if (next.src) {
              next.onload = () => resolve();
              next.onerror = () => reject(new Error("脚本加载失败"));
            } else {
              next.text = script.textContent || "";
              resolve();
            }
            script.replaceWith(next);
          });
        }
      }
    } catch (err) {
      setError((err as { message?: string }).message || "操作失败，请稍后再试");
    } finally {
      setCheckoutLoading(null);
    }
  }

  const isPaidCurrent = currentPlan !== "free";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-4xl gap-0 overflow-hidden rounded-shell border-line bg-white p-0 shadow-card">
        <DialogHeader className="space-y-3 border-b border-line px-6 pb-4 pt-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <DialogTitle className="font-heading text-xl font-extrabold tracking-[-0.03em] text-ink">
              升级套餐
            </DialogTitle>
            <div className="inline-flex items-center gap-1 rounded-full border border-line bg-white p-1 shadow-sm">
              <button
                type="button"
                onClick={() => setBillingCycle("monthly")}
                className={[
                  "rounded-full px-3 py-1 text-xs font-semibold transition",
                  billingCycle === "monthly"
                    ? "bg-ink text-white"
                    : "text-soft hover:text-ink",
                ].join(" ")}
              >
                月付
              </button>
              <button
                type="button"
                onClick={() => setBillingCycle("annual")}
                className={[
                  "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition",
                  billingCycle === "annual"
                    ? "bg-ink text-white"
                    : "text-soft hover:text-ink",
                ].join(" ")}
              >
                年付
                <span
                  className={[
                    "rounded-full px-1.5 py-0.5 text-[10px] font-bold",
                    billingCycle === "annual"
                      ? "bg-[#d94d72] text-white"
                      : "bg-emerald-100 text-emerald-700",
                  ].join(" ")}
                >
                  -20%
                </span>
              </button>
            </div>
          </div>
        </DialogHeader>

        <div className="max-h-[calc(90vh-160px)] overflow-y-auto px-6 py-6">
          {/* 套餐卡片区 */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PLAN_ORDER.map((key) => {
              const plan = PLANS[key];
              const isPro = key === "pro";
              const isCurrent = key === currentPlan;
              const price = priceLabel(plan, billingCycle);
              const perLabel =
                plan.monthlyUsd === 0
                  ? ""
                  : billingCycle === "annual"
                  ? "/月，按年结算"
                  : "/月";

              let cta: React.ReactNode = null;
              if (isCurrent) {
                cta = (
                  <button
                    type="button"
                    disabled
                    className="mt-4 inline-flex w-full items-center justify-center rounded-pill border border-line bg-line/40 px-4 py-2 text-xs font-semibold text-soft"
                  >
                    当前套餐
                  </button>
                );
              } else if (key === "free" && isPaidCurrent) {
                cta = null;
              } else if (key === "team") {
                cta = (
                  <a
                    href="mailto:hello@clueai.co"
                    className="mt-4 inline-flex w-full items-center justify-center rounded-pill border border-line bg-white px-4 py-2 text-xs font-semibold text-ink shadow-sm transition hover:border-ink/20"
                  >
                    联系销售
                  </a>
                );
              } else if (!isPaidCurrent) {
                cta = (
                  <Link
                    href={`/register?plan=${key}`}
                    onClick={() => onOpenChange(false)}
                    className={[
                      "mt-4 inline-flex w-full items-center justify-center rounded-pill px-4 py-2 text-xs font-semibold shadow-card transition",
                      isPro
                        ? "bg-[#d94d72] text-white hover:bg-[#c4405f]"
                        : "border border-line bg-white text-ink hover:border-ink/20",
                    ].join(" ")}
                  >
                    立即升级
                  </Link>
                );
              } else {
                cta = (
                  <button
                    type="button"
                    onClick={() => handlePaidCheckout(key)}
                    disabled={checkoutLoading !== null}
                    className={[
                      "mt-4 inline-flex w-full items-center justify-center rounded-pill px-4 py-2 text-xs font-semibold shadow-card transition disabled:opacity-50",
                      isPro
                        ? "bg-[#d94d72] text-white hover:bg-[#c4405f]"
                        : "border border-line bg-white text-ink hover:border-ink/20",
                    ].join(" ")}
                  >
                    {checkoutLoading === key ? "加载中..." : "升级套餐"}
                  </button>
                );
              }

              return (
                <article
                  key={key}
                  className={[
                    "relative flex flex-col rounded-shell border p-5 shadow-card",
                    isPro
                      ? "border-2 border-[#d94d72] bg-white"
                      : "border-line bg-white/86",
                  ].join(" ")}
                >
                  {isPro && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-pill bg-[#d94d72] px-3 py-0.5 text-[10px] font-bold tracking-wider text-white">
                      最受欢迎
                    </div>
                  )}

                  <div className="text-xs font-semibold uppercase tracking-[0.14em] text-soft">
                    {PLAN_NAME_CN[key]}
                  </div>

                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
                      {price}
                    </span>
                    {perLabel && (
                      <span className="text-[11px] font-medium text-soft">
                        {perLabel}
                      </span>
                    )}
                  </div>

                  <div className="mt-1 text-xs text-soft">
                    {plan.credits.toLocaleString()} credits / 月
                  </div>

                  {billingCycle === "annual" && plan.annualTotalUsd > 0 && (
                    <div className="mt-0.5 text-[11px] text-soft">
                      ${plan.annualTotalUsd} 按年支付
                    </div>
                  )}

                  {cta}

                  <ul className="mt-4 space-y-1.5 border-t border-line pt-4">
                    {PLAN_HIGHLIGHTS[key].map((line) => (
                      <li
                        key={line}
                        className="flex items-start gap-1.5 text-xs leading-5 text-ink"
                      >
                        <Check
                          size={13}
                          className="mt-0.5 shrink-0 text-[#4a7dc7]"
                          strokeWidth={2.5}
                        />
                        <span>{line}</span>
                      </li>
                    ))}
                  </ul>
                </article>
              );
            })}
          </div>

          {/* 功能对比表 */}
          <div className="mt-8 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-0 text-sm">
              <thead>
                <tr>
                  <th
                    scope="col"
                    className="sticky left-0 z-10 min-w-[160px] border-b border-line bg-white px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-soft"
                  >
                    功能对比
                  </th>
                  {PLAN_ORDER.map((key) => (
                    <th
                      key={key}
                      scope="col"
                      className={[
                        "border-b border-line px-4 py-3 text-center text-xs font-semibold",
                        key === "pro" ? "text-[#d94d72]" : "text-ink",
                      ].join(" ")}
                    >
                      {PLAN_NAME_CN[key]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {COMPARISON_GROUPS.map((group) => (
                  <Fragment key={group.title}>
                    <tr>
                      <th
                        scope="colgroup"
                        colSpan={5}
                        className="sticky left-0 bg-hero-wash px-4 py-2 text-left text-xs font-semibold text-soft"
                      >
                        {group.title}
                      </th>
                    </tr>
                    {group.rows.map((row) => (
                      <tr key={row.label} className="border-t border-line">
                        <th
                          scope="row"
                          className="sticky left-0 z-10 bg-white px-4 py-2.5 text-left text-xs font-medium text-ink"
                        >
                          {row.label}
                        </th>
                        {PLAN_ORDER.map((planKey) => {
                          const value = row.values[planKey];
                          return (
                            <td
                              key={planKey}
                              className="px-4 py-2.5 text-center text-xs text-ink tabular-nums"
                            >
                              {value === true ? (
                                <Check
                                  size={14}
                                  className="mx-auto text-[#4a7dc7]"
                                  strokeWidth={2.5}
                                />
                              ) : value === false ? (
                                <Minus
                                  size={14}
                                  className="mx-auto text-soft/60"
                                  strokeWidth={2}
                                />
                              ) : (
                                <span>{value}</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <div className="flex flex-col gap-2 border-t border-line bg-[#f8f6f3] px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          {error ? (
            <p className="text-xs text-red-600">{error}</p>
          ) : (
            <span className="text-xs text-soft">
              升级后新配额立即生效，Top-up credits 永不过期。
            </span>
          )}
          <button
            type="button"
            onClick={onOpenLedger}
            className="text-xs font-semibold text-rose hover:underline"
          >
            查看消费记录 →
          </button>
        </div>

        <div ref={checkoutRef} className="hidden" aria-hidden="true" />
      </DialogContent>
    </Dialog>
  );
}
