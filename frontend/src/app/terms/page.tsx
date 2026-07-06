import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Terms of Service | ClueAI",
  description: "ClueAI terms of service — service scope, responsibilities, and usage rules.",
  path: "/terms",
});

export default function TermsPage() {
  return (
    <MarketingShell title="Terms of Service" description="Service scope, responsibilities, and usage rules.">
      <article className="prose prose-sm mx-auto max-w-3xl px-4 py-12">
        <h1>用户协议 / Terms of Service</h1>
        <p className="text-muted-foreground">最后更新 / Last Updated：2026 年 7 月 6 日 / July 6, 2026</p>

        <h2>一、服务范围 / 1. Scope of Service</h2>
        <p>ClueAI（以下简称&quot;本服务&quot;）为跨境电商卖家提供：</p>
        <ul>
          <li>产品评论智能分析（情感分析、维度提取、趋势洞察）</li>
          <li>AI 问答（基于评论数据的自然语言查询）</li>
          <li>广告文案生成（基于评论洞察的营销内容）</li>
          <li>产品对比分析</li>
          <li>预警通知（飞书/钉钉/企业微信 Webhook）</li>
          <li>数据导出（Excel 格式）</li>
        </ul>
        <p className="text-muted-foreground">ClueAI (&quot;the Service&quot;) provides cross-border e-commerce sellers with:</p>
        <ul className="text-muted-foreground">
          <li>Intelligent product review analysis (sentiment analysis, dimension extraction, trend insights)</li>
          <li>AI Q&A (natural language queries based on review data)</li>
          <li>Ad copy generation (marketing content based on review insights)</li>
          <li>Product comparison analysis</li>
          <li>Alert notifications (Feishu / DingTalk / WeCom Webhook)</li>
          <li>Data export (Excel format)</li>
        </ul>

        <h2>二、账户与使用规则 / 2. Account & Usage Rules</h2>
        <ul>
          <li>每人限注册一个账户，不得转让或共享账户</li>
          <li>您对账户下的所有活动负责</li>
          <li>禁止利用本服务进行违法活动、侵犯他人知识产权</li>
          <li>禁止通过自动化手段绕过配额限制或滥用 API</li>
          <li>禁止上传违法、侵权或恶意内容</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>Each person is limited to one account; accounts may not be transferred or shared</li>
          <li>You are responsible for all activities under your account</li>
          <li>Using the Service for illegal activities or intellectual property infringement is prohibited</li>
          <li>Circumventing quota limits or abusing the API through automated means is prohibited</li>
          <li>Uploading illegal, infringing, or malicious content is prohibited</li>
        </ul>

        <h2>三、套餐与计费 / 3. Plans & Billing</h2>
        <ul>
          <li>Free 套餐：免费使用，受配额限制</li>
          <li>Pro / Team 套餐：按月或按年订阅，通过 Paddle 平台计费</li>
          <li>订阅自动续费，可随时取消（取消后当前周期仍可使用至到期）</li>
          <li>配额按自然月重置，不结转、不退还</li>
          <li>价格调整提前 30 天通知</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>Free plan: free to use with quota limits</li>
          <li>Pro / Team plans: monthly or annual subscription, billed through the Paddle platform</li>
          <li>Subscriptions renew automatically; you may cancel at any time (access continues until the end of the current billing cycle)</li>
          <li>Quota resets monthly and does not carry over or qualify for refunds</li>
          <li>Price adjustments will be notified 30 days in advance; early-bird users enjoy price-lock benefits</li>
        </ul>

        <h2>四、数据所有权 / 4. Data Ownership</h2>
        <ul>
          <li>您上传的评论数据归您所有</li>
          <li>AI 分析生成的结果归您所有</li>
          <li>我们不会将您的数据用于训练 AI 模型</li>
          <li>我们有权使用匿名化聚合数据改进服务质量</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>Review data you upload remains your property</li>
          <li>AI-generated analysis results belong to you</li>
          <li>We will not use your data to train AI models</li>
          <li>We may use anonymized aggregate data to improve service quality</li>
        </ul>

        <h2>五、服务可用性 / 5. Service Availability</h2>
        <ul>
          <li>我们目标 99.5% 月度可用性，但不做绝对保证</li>
          <li>计划维护提前 24 小时通知</li>
          <li>因不可抗力（网络故障、第三方 API 中断）导致的服务中断不属于违约</li>
          <li>AI 分析结果仅供参考，不构成商业决策建议</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>We target 99.5% monthly uptime but do not guarantee absolute availability</li>
          <li>Scheduled maintenance will be notified 24 hours in advance</li>
          <li>Service interruptions caused by force majeure (network failures, third-party API outages) do not constitute a breach</li>
          <li>AI analysis results are for reference only and do not constitute business advice</li>
        </ul>

        <h2>六、责任边界 / 6. Limitation of Liability</h2>
        <ul>
          <li>本服务按&quot;现状&quot;提供，不对分析准确性做绝对保证</li>
          <li>因使用本服务分析结果做出的商业决策，由用户自行承担风险</li>
          <li>我们的赔偿上限为您过去 12 个月支付的服务费用总额</li>
          <li>不对间接损失、预期利润损失承担责任</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>The Service is provided &quot;as is&quot; without absolute guarantees of analysis accuracy</li>
          <li>Business decisions made based on the Service&apos;s analysis results are at your own risk</li>
          <li>Our maximum liability is limited to the total service fees paid by you in the preceding 12 months</li>
          <li>We are not liable for indirect losses or loss of anticipated profits</li>
        </ul>

        <h2>七、知识产权 / 7. Intellectual Property</h2>
        <ul>
          <li>ClueAI 平台的软件、设计、算法归我方所有</li>
          <li>您不得反编译、逆向工程或复制本服务</li>
          <li>用户反馈和建议可能被采纳用于改进产品，无需额外补偿</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>The ClueAI platform software, design, and algorithms are our property</li>
          <li>You may not decompile, reverse engineer, or copy the Service</li>
          <li>User feedback and suggestions may be used to improve the product without additional compensation</li>
        </ul>

        <h2>八、账户终止 / 8. Account Termination</h2>
        <ul>
          <li>您可随时注销账户，注销后 30 天内删除所有数据</li>
          <li>违反本协议的，我们有权暂停或终止服务</li>
          <li>严重违规（如恶意攻击、数据爬取）可立即终止且不退款</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>You may delete your account at any time; all data will be removed within 30 days</li>
          <li>We reserve the right to suspend or terminate service for violations of this agreement</li>
          <li>Severe violations (e.g., malicious attacks, data scraping) may result in immediate termination without refund</li>
        </ul>

        <h2>九、争议解决 / 9. Dispute Resolution</h2>
        <ul>
          <li>本协议适用中华人民共和国法律</li>
          <li>争议优先协商解决</li>
          <li>协商不成的，提交被告所在地有管辖权的人民法院诉讼</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>This agreement is governed by the laws of the People&apos;s Republic of China</li>
          <li>Disputes shall be resolved through negotiation first</li>
          <li>If negotiation fails, disputes shall be submitted to a court of competent jurisdiction at the defendant&apos;s location</li>
        </ul>

        <h2>十、联系方式 / 10. Contact Us</h2>
        <p>
          如有问题或投诉，请联系：<a href="mailto:support@clueai-reviewlens.com">support@clueai-reviewlens.com</a>
        </p>
        <p className="text-muted-foreground">
          For questions or complaints, please contact: <a href="mailto:support@clueai-reviewlens.com">support@clueai-reviewlens.com</a>
        </p>
      </article>
    </MarketingShell>
  );
}
