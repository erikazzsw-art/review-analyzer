import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Terms of Service | ClueAI",
  description: "ClueAI terms of service — service scope, responsibilities, and usage rules.",
  path: "/terms",
});

export default function TermsPage() {
  return (
    <MarketingShell>
      <article className="prose prose-sm mx-auto max-w-3xl px-4 py-12">
        <h1>用户协议</h1>
        <p className="text-muted-foreground">最后更新：2026 年 6 月 10 日</p>

        <h2>一、服务范围</h2>
        <p>ClueAI（以下简称"本服务"）为跨境电商卖家提供：</p>
        <ul>
          <li>产品评论智能分析（情感分析、维度提取、趋势洞察）</li>
          <li>AI 问答（基于评论数据的自然语言查询）</li>
          <li>广告文案生成（基于评论洞察的营销内容）</li>
          <li>产品对比分析</li>
          <li>预警通知（飞书/钉钉/企业微信 Webhook）</li>
          <li>数据导出（Excel 格式）</li>
        </ul>

        <h2>二、账户与使用规则</h2>
        <ul>
          <li>每人限注册一个账户，不得转让或共享账户</li>
          <li>您对账户下的所有活动负责</li>
          <li>禁止利用本服务进行违法活动、侵犯他人知识产权</li>
          <li>禁止通过自动化手段绕过配额限制或滥用 API</li>
          <li>禁止上传违法、侵权或恶意内容</li>
        </ul>

        <h2>三、套餐与计费</h2>
        <ul>
          <li>Free 套餐：免费使用，受配额限制</li>
          <li>Pro / Team 套餐：按月订阅，通过 Paddle 平台计费</li>
          <li>订阅自动续费，可随时取消（取消后当前周期仍可使用至到期）</li>
          <li>配额按自然月重置，不结转、不退还</li>
          <li>价格调整提前 30 天通知，早鸟用户享锁价权益</li>
        </ul>

        <h2>四、数据所有权</h2>
        <ul>
          <li>您上传的评论数据归您所有</li>
          <li>AI 分析生成的结果归您所有</li>
          <li>我们不会将您的数据用于训练 AI 模型</li>
          <li>我们有权使用匿名化聚合数据改进服务质量</li>
        </ul>

        <h2>五、服务可用性</h2>
        <ul>
          <li>我们目标 99.5% 月度可用性，但不做绝对保证</li>
          <li>计划维护提前 24 小时通知</li>
          <li>因不可抗力（网络故障、第三方 API 中断）导致的服务中断不属于违约</li>
          <li>AI 分析结果仅供参考，不构成商业决策建议</li>
        </ul>

        <h2>六、责任边界</h2>
        <ul>
          <li>本服务按"现状"提供，不对分析准确性做绝对保证</li>
          <li>因使用本服务分析结果做出的商业决策，由用户自行承担风险</li>
          <li>我们的赔偿上限为您过去 12 个月支付的服务费用总额</li>
          <li>不对间接损失、预期利润损失承担责任</li>
        </ul>

        <h2>七、知识产权</h2>
        <ul>
          <li>ClueAI 平台的软件、设计、算法归我方所有</li>
          <li>您不得反编译、逆向工程或复制本服务</li>
          <li>用户反馈和建议可能被采纳用于改进产品，无需额外补偿</li>
        </ul>

        <h2>八、账户终止</h2>
        <ul>
          <li>您可随时注销账户，注销后 30 天内删除所有数据</li>
          <li>违反本协议的，我们有权暂停或终止服务</li>
          <li>严重违规（如恶意攻击、数据爬取）可立即终止且不退款</li>
        </ul>

        <h2>九、争议解决</h2>
        <ul>
          <li>本协议适用中华人民共和国法律</li>
          <li>争议优先协商解决</li>
          <li>协商不成的，提交被告所在地有管辖权的人民法院诉讼</li>
        </ul>

        <h2>十、联系方式</h2>
        <p>如有问题或投诉，请联系：<a href="mailto:support@clueai-reviewlens.com">support@clueai-reviewlens.com</a></p>
      </article>
    </MarketingShell>
  );
}
