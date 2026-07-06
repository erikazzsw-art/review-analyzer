import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Refund Policy | ClueAI",
  description: "ClueAI refund policy — subscription cancellation, refund conditions, and process.",
  path: "/refund",
});

export default function RefundPage() {
  return (
    <MarketingShell title="Refund Policy" description="Subscription cancellation, refund conditions, and process.">
      <article className="prose prose-sm mx-auto max-w-3xl px-4 py-12">
        <h1>退款政策 / Refund Policy</h1>
        <p className="text-muted-foreground">最后更新 / Last Updated：2026 年 7 月 6 日 / July 6, 2026</p>

        <p>
          感谢您选择 ClueAI。我们致力于为跨境电商卖家提供优质的评论分析服务。以下是我们的退款政策，请在订阅前仔细阅读。
        </p>
        <p className="text-muted-foreground">
          Thank you for choosing ClueAI. We are committed to providing quality review analysis services for cross-border e-commerce sellers. Please read our refund policy carefully before subscribing.
        </p>

        <hr />

        <h2>一、订阅与计费 / 1. Subscription & Billing</h2>
        <ul>
          <li>ClueAI 提供 Free（免费）、Pro 和 Team 三种套餐</li>
          <li>付费套餐通过 Paddle 平台处理支付，支持月付和年付</li>
          <li>订阅自动续费，您可在当前计费周期结束前随时取消</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>ClueAI offers three plans: Free, Pro, and Team</li>
          <li>Paid plans are processed through the Paddle payment platform, with monthly and annual billing options</li>
          <li>Subscriptions renew automatically; you may cancel at any time before the end of the current billing cycle</li>
        </ul>

        <h2>二、月付订阅退款 / 2. Monthly Subscription Refunds</h2>
        <ul>
          <li>月付订阅一经扣款，<strong>不予退款</strong></li>
          <li>取消后，您仍可在当前计费周期结束前继续使用所有付费功能</li>
          <li>计费周期结束后，账户将自动降级为 Free 套餐</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>Monthly subscriptions are <strong>non-refundable</strong> once payment has been processed</li>
          <li>After cancellation, you may continue using all paid features until the end of the current billing cycle</li>
          <li>After the billing cycle ends, your account will be automatically downgraded to the Free plan</li>
        </ul>

        <h2>三、年付订阅退款 / 3. Annual Subscription Refunds</h2>
        <ul>
          <li>年付订阅在首次付款后 <strong>7 天内</strong>，如未使用付费功能（分析配额消耗为零），可申请全额退款</li>
          <li>超过 7 天或已使用付费功能的，按剩余完整月份比例退款（已开始的月份不予退还）</li>
          <li>使用超过 6 个月的年付订阅不予退款，但可取消自动续费</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>Annual subscriptions may be fully refunded within <strong>7 days</strong> of the initial payment, provided no paid features have been used (zero quota consumption)</li>
          <li>After 7 days or if paid features have been used, refunds are prorated based on the remaining full months (partial months are non-refundable)</li>
          <li>Annual subscriptions used for more than 6 months are non-refundable, but auto-renewal can be cancelled</li>
        </ul>

        <h2>四、不予退款的情况 / 4. Non-Refundable Circumstances</h2>
        <ul>
          <li>违反用户协议导致账户被封禁的</li>
          <li>已消耗的分析配额（配额不结转、不退还）</li>
          <li>因用户自身原因（如忘记取消续费）导致的扣款</li>
          <li>套餐降级产生的差价</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>Account suspension due to violation of Terms of Service</li>
          <li>Consumed analysis quota (quota does not carry over and is non-refundable)</li>
          <li>Charges incurred due to user&apos;s own oversight (e.g., forgetting to cancel renewal)</li>
          <li>Price differences from plan downgrades</li>
        </ul>

        <h2>五、退款流程 / 5. Refund Process</h2>
        <ol>
          <li>发送邮件至 <a href="mailto:support@clueai-reviewlens.com">support@clueai-reviewlens.com</a>，注明账户邮箱、订阅类型和退款原因</li>
          <li>我们将在 <strong>3 个工作日</strong>内审核您的退款申请</li>
          <li>审核通过后，退款将通过原支付渠道（Paddle）退回，预计 <strong>5–10 个工作日</strong>到账</li>
        </ol>
        <ol className="text-muted-foreground">
          <li>Send an email to <a href="mailto:support@clueai-reviewlens.com">support@clueai-reviewlens.com</a> with your account email, subscription type, and reason for the refund</li>
          <li>We will review your refund request within <strong>3 business days</strong></li>
          <li>Once approved, the refund will be processed through the original payment channel (Paddle) and is expected to arrive within <strong>5–10 business days</strong></li>
        </ol>

        <h2>六、取消订阅 / 6. Cancellation</h2>
        <ul>
          <li>您可以随时在账户设置中取消订阅</li>
          <li>取消后不会再产生新的扣款</li>
          <li>当前已付费周期内的服务不受影响，可继续使用至到期</li>
          <li>到期后账户自动降级为 Free 套餐，历史数据保留</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>You may cancel your subscription at any time in your account settings</li>
          <li>No further charges will be incurred after cancellation</li>
          <li>Service for the current paid period remains unaffected; you may continue using it until expiry</li>
          <li>After expiry, your account will be automatically downgraded to the Free plan; historical data will be retained</li>
        </ul>

        <h2>七、政策变更 / 7. Policy Changes</h2>
        <p>
          我们保留随时修改本退款政策的权利。变更将通过网站公告或邮件通知。修改后继续使用本服务即视为接受更新后的政策。
        </p>
        <p className="text-muted-foreground">
          We reserve the right to modify this refund policy at any time. Changes will be communicated via website announcements or email notifications. Continued use of the service after modifications constitutes acceptance of the updated policy.
        </p>

        <h2>八、联系我们 / 8. Contact Us</h2>
        <p>
          如有退款相关问题，请联系：<a href="mailto:support@clueai-reviewlens.com">support@clueai-reviewlens.com</a>
        </p>
        <p className="text-muted-foreground">
          For any refund-related questions, please contact: <a href="mailto:support@clueai-reviewlens.com">support@clueai-reviewlens.com</a>
        </p>
      </article>
    </MarketingShell>
  );
}
