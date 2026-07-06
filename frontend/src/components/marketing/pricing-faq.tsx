"use client";

import { useState } from "react";

const faqs = [
  {
    q: "免费版有什么限制？",
    a: "免费版支持 1 个产品组、每次最多 50 条评论分析，分析历史保留 7 天。适合个人卖家快速体验核心功能。",
  },
  {
    q: "Pro 版按月付费还是按年？",
    a: "目前 Pro 按月订阅（$19/月 / 约 ¥138），通过 Paddle 全球安全结算，可随时取消。后续会推出年付优惠方案。",
  },
  {
    q: "升级后原来的数据还在吗？",
    a: "升级后所有历史分析数据自动保留并解除 7 天过期限制，无需重新上传。",
  },
  {
    q: "支持哪些支付方式？",
    a: "国际信用卡、PayPal 等主流方式均通过 Paddle 平台支持。企业客户可联系我们获取年度合同。",
  },
  {
    q: "Team 方案最少几个人起？",
    a: "Team 方案 3 人起，按需定制。联系我们获取专属报价和功能演示。",
  },
  {
    q: "可以随时降级或取消吗？",
    a: "可以。降级后当前计费周期结束前仍享有 Pro 功能，到期后自动回到 Free 版。数据不会丢失。",
  },
];

export function PricingFaq() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="mx-auto w-full max-w-3xl px-6 pb-20 lg:px-10">
      <h2 className="font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
        常见问题
      </h2>
      <div className="mt-8 divide-y divide-line">
        {faqs.map((faq, index) => (
          <div key={index}>
            <button
              type="button"
              onClick={() =>
                setOpenIndex(openIndex === index ? null : index)
              }
              className="flex w-full items-center justify-between py-5 text-left text-sm font-semibold text-ink transition hover:text-[#4a7dc7]"
            >
              <span>{faq.q}</span>
              <svg
                className={[
                  "h-4 w-4 shrink-0 text-soft transition-transform",
                  openIndex === index ? "rotate-180" : "",
                ].join(" ")}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
            {openIndex === index && (
              <p className="pb-5 text-sm leading-7 text-soft">{faq.a}</p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
