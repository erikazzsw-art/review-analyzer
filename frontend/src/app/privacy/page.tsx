import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Privacy Policy | ClueAI",
  description: "ClueAI privacy policy — how we collect, use, and protect your data.",
  path: "/privacy",
});

export default function PrivacyPage() {
  return (
    <MarketingShell title="Privacy Policy" description="How we collect, use, and protect your data.">
      <article className="prose prose-sm mx-auto max-w-3xl px-4 py-12">
        <h1>隐私协议 / Privacy Policy</h1>
        <p className="text-muted-foreground">最后更新 / Last Updated：2026 年 7 月 7 日 / July 7, 2026</p>

        <h2>一、我们收集的信息 / 1. Information We Collect</h2>
        <ul>
          <li><strong>账户信息</strong>：注册时提供的用户名、邮箱地址</li>
          <li><strong>业务数据</strong>：您上传的产品评论内容、分析结果、产品档案</li>
          <li><strong>使用数据</strong>：功能使用频率、配额消耗、登录时间等聚合统计</li>
          <li><strong>技术数据</strong>：IP 地址、浏览器类型、设备信息（用于安全防护）</li>
        </ul>
        <ul className="text-muted-foreground">
          <li><strong>Account Information</strong>: Username and email address provided during registration</li>
          <li><strong>Business Data</strong>: Product review content you upload, analysis results, and product profiles</li>
          <li><strong>Usage Data</strong>: Aggregated statistics such as feature usage frequency, quota consumption, and login times</li>
          <li><strong>Technical Data</strong>: IP address, browser type, and device information (for security purposes)</li>
        </ul>

        <h2>二、信息使用目的 / 2. How We Use Your Information</h2>
        <ul>
          <li>提供评论分析、AI 问答、广告文案生成等核心服务</li>
          <li>维护账户安全和服务稳定性</li>
          <li>改进产品功能和用户体验</li>
          <li>发送服务相关通知（如配额提醒、系统维护）</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>Delivering core services including review analysis, AI Q&A, and ad copy generation</li>
          <li>Maintaining account security and service stability</li>
          <li>Improving product features and user experience</li>
          <li>Sending service-related notifications (e.g., quota reminders, system maintenance)</li>
        </ul>

        <h2>三、第三方共享 / 3. Third-Party Sharing</h2>
        <p>我们不会出售您的个人数据。以下情况可能涉及第三方处理：</p>
        <p className="text-muted-foreground">We do not sell your personal data. Third-party processing may occur in the following cases:</p>
        <ul>
          <li><strong>AI 分析服务</strong>：评论内容发送至 DeepSeek API 进行语义分析，仅传输文本内容，不含个人身份信息</li>
          <li><strong>支付处理</strong>：通过 Paddle 处理订阅付款，Paddle 独立处理支付信息</li>
          <li><strong>基础设施</strong>：数据存储于 Supabase（PostgreSQL）和阿里云 ECS，均有行业标准安全措施</li>
          <li><strong>法律要求</strong>：在法律强制要求时，我们可能披露必要信息</li>
        </ul>
        <ul className="text-muted-foreground">
          <li><strong>AI Analysis</strong>: Review content is sent to the DeepSeek API for semantic analysis; only text content is transmitted without personally identifiable information</li>
          <li><strong>Payment Processing</strong>: Subscription payments are processed through Paddle, which independently handles payment information</li>
          <li><strong>Infrastructure</strong>: Data is stored on Supabase (PostgreSQL) and Alibaba Cloud ECS, both with industry-standard security measures</li>
          <li><strong>Legal Requirements</strong>: We may disclose necessary information when legally required</li>
        </ul>

        <h2>四、分析结果聚合复用 / 4. Aggregated Analysis Reuse</h2>
        <p>为提升分析速度、降低成本，当您上传的评论与其他用户已分析过的评论<strong>内容完全相同</strong>时（基于文本哈希匹配），我们可能直接复用已有的分析结果，不再重复调用 AI 模型。</p>
        <ul>
          <li>复用仅涉及匿名化的分析输出（情感倾向、观点标签、方面维度），<strong>不涉及</strong>任何用户身份、上传时间、账号信息的跨用户共享</li>
          <li>复用不影响您的评论额度扣减 —— 额度按您上传的条数正常消费</li>
          <li>您可通过账户设置发起数据删除请求，我们会在 30 天内清除您上传的原始评论；聚合分析结果（脱敏后）可能继续用于服务</li>
        </ul>
        <p className="text-muted-foreground">To improve analysis speed and reduce cost, when reviews you upload have <strong>identical content</strong> to reviews already analyzed by other users (matched via content hash), we may reuse the existing analysis results rather than calling the AI model again.</p>
        <ul className="text-muted-foreground">
          <li>Reuse involves only anonymized analysis output (sentiment, aspect tags, opinion dimensions). <strong>No</strong> user identity, upload timestamp, or account information is shared across users.</li>
          <li>Reuse does not affect your review quota — quota is consumed based on the number of reviews you upload, regardless of cache hits.</li>
          <li>You may request data deletion via account settings; we will remove the raw reviews you uploaded within 30 days. Anonymized aggregated analysis results may be retained for service delivery.</li>
        </ul>

        <h2>五、数据存储与安全 / 5. Data Storage & Security</h2>
        <ul>
          <li>数据加密存储，传输使用 TLS/SSL 加密</li>
          <li>API 密钥使用 AES/Fernet 加密后存储，不可逆向</li>
          <li>数据库实施行级安全（RLS），用户间数据完全隔离</li>
          <li>定期备份，备份数据加密存储于独立区域</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>Data is encrypted at rest and in transit using TLS/SSL</li>
          <li>API keys are stored with AES/Fernet encryption and cannot be reversed</li>
          <li>Row-Level Security (RLS) is implemented in the database, ensuring complete data isolation between users</li>
          <li>Regular backups are stored encrypted in separate regions</li>
        </ul>

        <h2>六、数据保留与删除 / 6. Data Retention & Deletion</h2>
        <ul>
          <li>账户存续期间保留您的数据</li>
          <li>账户注销后 30 天内删除所有个人数据和业务数据</li>
          <li>您可随时联系我们请求导出或删除数据</li>
          <li>匿名化聚合统计数据（无法识别个人）可能保留用于改进服务</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>Your data is retained for the duration of your account</li>
          <li>All personal and business data will be deleted within 30 days after account deletion</li>
          <li>You may contact us at any time to request data export or deletion</li>
          <li>Anonymized aggregate statistics (which cannot identify individuals) may be retained for service improvement</li>
        </ul>

        <h2>七、您的权利 / 7. Your Rights</h2>
        <p>根据《中华人民共和国个人信息保护法》及 GDPR，您享有：</p>
        <p className="text-muted-foreground">Under China&apos;s Personal Information Protection Law (PIPL) and GDPR, you have the right to:</p>
        <ul>
          <li>查阅、复制您的个人信息</li>
          <li>更正不准确的信息</li>
          <li>删除您的个人信息</li>
          <li>撤回同意</li>
          <li>数据可携带（导出为通用格式）</li>
        </ul>
        <ul className="text-muted-foreground">
          <li>Access and copy your personal information</li>
          <li>Correct inaccurate information</li>
          <li>Delete your personal information</li>
          <li>Withdraw consent</li>
          <li>Data portability (export in common formats)</li>
        </ul>

        <h2>八、Cookie 使用 / 8. Cookies</h2>
        <p>我们使用必要的会话 Cookie 维持登录状态，不使用第三方追踪 Cookie。</p>
        <p className="text-muted-foreground">We use essential session cookies to maintain login status. We do not use third-party tracking cookies.</p>

        <h2>九、未成年人保护 / 9. Protection of Minors</h2>
        <p>本服务面向企业用户，不面向 16 岁以下未成年人。如发现误收集未成年人信息，将立即删除。</p>
        <p className="text-muted-foreground">This Service is designed for business users and is not intended for minors under 16. If we discover that information from minors has been inadvertently collected, it will be deleted immediately.</p>

        <h2>十、协议变更 / 10. Policy Changes</h2>
        <p>协议更新时，我们会通过邮件或站内通知告知。继续使用服务视为接受更新后的协议。</p>
        <p className="text-muted-foreground">We will notify you of policy updates via email or in-app notifications. Continued use of the Service constitutes acceptance of the updated policy.</p>

        <h2>十一、联系方式 / 11. Contact Us</h2>
        <p>
          如有隐私相关问题，请联系：<a href="mailto:privacy@clueai-reviewlens.com">privacy@clueai-reviewlens.com</a>
        </p>
        <p className="text-muted-foreground">
          For privacy-related inquiries, please contact: <a href="mailto:privacy@clueai-reviewlens.com">privacy@clueai-reviewlens.com</a>
        </p>
      </article>
    </MarketingShell>
  );
}
