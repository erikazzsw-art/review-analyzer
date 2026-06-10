import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Privacy Policy | ClueAI",
  description: "ClueAI privacy policy — how we collect, use, and protect your data.",
  path: "/privacy",
});

export default function PrivacyPage() {
  return (
    <MarketingShell>
      <article className="prose prose-sm mx-auto max-w-3xl px-4 py-12">
        <h1>隐私协议</h1>
        <p className="text-muted-foreground">最后更新：2026 年 6 月 10 日</p>

        <h2>一、我们收集的信息</h2>
        <ul>
          <li><strong>账户信息</strong>：注册时提供的用户名、邮箱地址</li>
          <li><strong>业务数据</strong>：您上传的产品评论内容、分析结果、产品档案</li>
          <li><strong>使用数据</strong>：功能使用频率、配额消耗、登录时间等聚合统计</li>
          <li><strong>技术数据</strong>：IP 地址、浏览器类型、设备信息（用于安全防护）</li>
        </ul>

        <h2>二、信息使用目的</h2>
        <ul>
          <li>提供评论分析、AI 问答、广告文案生成等核心服务</li>
          <li>维护账户安全和服务稳定性</li>
          <li>改进产品功能和用户体验</li>
          <li>发送服务相关通知（如配额提醒、系统维护）</li>
        </ul>

        <h2>三、第三方共享</h2>
        <p>我们不会出售您的个人数据。以下情况可能涉及第三方处理：</p>
        <ul>
          <li><strong>AI 分析服务</strong>：评论内容发送至 DeepSeek API 进行语义分析，仅传输文本内容，不含个人身份信息</li>
          <li><strong>支付处理</strong>：通过 Paddle 处理订阅付款，Paddle 独立处理支付信息</li>
          <li><strong>基础设施</strong>：数据存储于 Supabase（PostgreSQL）和阿里云 ECS，均有行业标准安全措施</li>
          <li><strong>法律要求</strong>：在法律强制要求时，我们可能披露必要信息</li>
        </ul>

        <h2>四、数据存储与安全</h2>
        <ul>
          <li>数据加密存储，传输使用 TLS/SSL 加密</li>
          <li>API 密钥使用 AES/Fernet 加密后存储，不可逆向</li>
          <li>数据库实施行级安全（RLS），用户间数据完全隔离</li>
          <li>定期备份，备份数据加密存储于独立区域</li>
        </ul>

        <h2>五、数据保留与删除</h2>
        <ul>
          <li>账户存续期间保留您的数据</li>
          <li>账户注销后 30 天内删除所有个人数据和业务数据</li>
          <li>您可随时联系我们请求导出或删除数据</li>
          <li>匿名化聚合统计数据（无法识别个人）可能保留用于改进服务</li>
        </ul>

        <h2>六、您的权利</h2>
        <p>根据《中华人民共和国个人信息保护法》及 GDPR，您享有：</p>
        <ul>
          <li>查阅、复制您的个人信息</li>
          <li>更正不准确的信息</li>
          <li>删除您的个人信息</li>
          <li>撤回同意</li>
          <li>数据可携带（导出为通用格式）</li>
        </ul>

        <h2>七、Cookie 使用</h2>
        <p>我们使用必要的会话 Cookie 维持登录状态，不使用第三方追踪 Cookie。</p>

        <h2>八、未成年人保护</h2>
        <p>本服务面向企业用户，不面向 16 岁以下未成年人。如发现误收集未成年人信息，将立即删除。</p>

        <h2>九、协议变更</h2>
        <p>协议更新时，我们会通过邮件或站内通知告知。继续使用服务视为接受更新后的协议。</p>

        <h2>十、联系方式</h2>
        <p>如有隐私相关问题，请联系：<a href="mailto:privacy@clueai-reviewlens.com">privacy@clueai-reviewlens.com</a></p>
      </article>
    </MarketingShell>
  );
}
