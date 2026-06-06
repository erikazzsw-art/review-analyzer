import Link from "next/link";

import { AppShell } from "@/components/app/app-shell";
import { CreateActionPanel } from "@/components/analysis/create-action-panel";
import { getAnalysisSessionResults } from "@/lib/api/server";
import { buildNoIndexMetadata } from "@/lib/seo";

export const metadata = buildNoIndexMetadata({
  title: "Analysis Results | ClueAI",
  description: "Authenticated analysis results for a single review batch.",
});

type ResultsPageProps = {
  searchParams?: Promise<{
    session_id?: string;
  }>;
};

function renderModuleLabel(key: string): string {
  const labels: Record<string, string> = {
    consumer_profile: "消费者画像",
    user_experience: "用户体验",
    purchase_motives: "购买动机",
    unmet_needs: "未被满足的需求",
    recommendations: "综合建议",
  };
  return labels[key] || key;
}

function renderModuleSubtitle(key: string): string {
  const labels: Record<string, string> = {
    consumer_profile: "从评论里提炼当前批次的核心人群、关注点与代表性证据。",
    user_experience: "拆出正向反馈和负向反馈，方便快速判断体验是否稳定。",
    purchase_motives: "概括用户为什么买，以及哪些卖点正在驱动下单。",
    unmet_needs: "聚焦还没被满足的需求，便于后续改版和运营动作。",
    recommendations: "把前面的信号收成可执行动作。",
  };
  return labels[key] || "";
}

function renderValue(value: unknown, fallback = "--"): string {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

export default async function AnalysisResultsPage({
  searchParams,
}: ResultsPageProps) {
  const params = searchParams ? await searchParams : undefined;
  const sessionId = Number(params?.session_id || 0);

  if (!sessionId) {
    return (
      <AppShell
        currentPath="/analysis/results"
        title="分析结果页需要一个 session_id。"
        description="M5 的结果页已经接到真实 API，URL 里带上 session_id 后就能直接打开对应批次。"
      >
        <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <p className="text-sm leading-7 text-soft">
            请输入有效的 `session_id`，例如从上传完成后的跳转链接或历史记录页进入。
          </p>
          <Link
            href="/analysis/history"
            className="mt-5 inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
          >
            去历史记录找一条
          </Link>
        </section>
      </AppShell>
    );
  }

  const payload = await getAnalysisSessionResults(sessionId);
  const context = payload.context as {
    product_id?: string;
    version?: string;
    time_label?: string;
    workflow_purpose?: string;
  };
  const consumerProfile = payload.modules.consumer_profile;
  const userExperience = payload.modules.user_experience;
  const purchaseMotives = payload.modules.purchase_motives;
  const unmetNeeds = payload.modules.unmet_needs;
  const recommendations = payload.modules.recommendations;
  const actionCandidates = [
    ...(userExperience.negative || []).map((row) => ({
      label: String(row.tag || row.label || "问题"),
      detail: String(row.reason || row.detail || row.pct || ""),
      currentPct: typeof row.pct === "number" ? row.pct : Number(row.pct) || null,
      suggestedAction: String(row.reason || row.detail || ""),
    })),
    ...(unmetNeeds.rows || []).map((row) => ({
      label: String(row.tag || row.label || "需求"),
      detail: String(row.reason || row.detail || row.summary || row.value || ""),
      currentPct: typeof row.pct === "number" ? row.pct : Number(row.pct) || null,
      suggestedAction: String(row.reason || row.detail || ""),
    })),
  ].slice(0, 5);

  return (
    <AppShell
      currentPath="/analysis/results"
      title="结果页现在可以按 session_id 直达真实分析内容。"
      description="这一版不再依赖页面隐式状态，结果、对比和历史都围绕 URL 和后端读取接口展开。"
    >
      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
          SESSION RESULTS
        </div>
        <h2 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          {payload.session.custom_title || payload.session.auto_title || payload.session.product_id}
        </h2>
        <div className="mt-4 flex flex-wrap gap-2">
          <span className="rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-soft">
            {renderValue(context.time_label)}
          </span>
          <span className="rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-soft">
            {renderValue(context.workflow_purpose, "未设置工作目的")}
          </span>
          <span className="rounded-pill border border-line bg-white px-3 py-2 text-xs font-semibold text-soft">
            {payload.comments.length} 条原文
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href={`/analysis/compare?product_id=${encodeURIComponent(payload.session.product_id)}&session_id=${sessionId}`}
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
          >
            去对比
          </Link>
          <Link
            href="/analysis/history"
            className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-ink"
          >
            回历史
          </Link>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <div className="rounded-card border border-line bg-white/84 p-5 shadow-card backdrop-blur">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">总评论</div>
          <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-ink">
            {payload.session.total_reviews}
          </div>
        </div>
        <div className="rounded-card border border-line bg-white/84 p-5 shadow-card backdrop-blur">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">好评</div>
          <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-[#4b8f82]">
            {payload.session.positive_count}
          </div>
        </div>
        <div className="rounded-card border border-line bg-white/84 p-5 shadow-card backdrop-blur">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">差评</div>
          <div className="mt-3 font-heading text-4xl font-extrabold tracking-[-0.04em] text-[#d94d72]">
            {payload.session.negative_count}
          </div>
        </div>
        <div className="rounded-card border border-line bg-white/84 p-5 shadow-card backdrop-blur">
          <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">工作目的</div>
          <div className="mt-3 text-sm leading-7 text-ink">
            {payload.session.workflow_purpose || "未设置"}
          </div>
        </div>
      </section>

      <CreateActionPanel
        sessionId={sessionId}
        productId={payload.session.product_ref_id}
        sourceProductId={payload.session.product_id}
        sourceVersion={payload.session.version}
        sourceBatchLabel={payload.session.custom_title || payload.session.auto_title || payload.session.version}
        candidates={actionCandidates}
      />

      <section className="space-y-5">
        <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
            1 · {renderModuleLabel("consumer_profile")}
          </div>
          <p className="mt-4 text-sm leading-7 text-soft">{consumerProfile.summary}</p>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {consumerProfile.rows.map((row, index) => (
              <div key={`consumer-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                  {renderValue(row.label || row.tag || `条目 ${index + 1}`)}
                </div>
                <div className="mt-2 text-sm leading-7 text-ink">
                  {renderValue(row.detail || row.reason || row.summary || row.value)}
                </div>
              </div>
            ))}
          </div>
          {consumerProfile.evidence.length > 0 ? (
            <div className="mt-5 rounded-card border border-line bg-[#fffafc] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                代表性证据
              </div>
              <div className="mt-3 space-y-2 text-sm leading-7 text-ink">
                {consumerProfile.evidence.map((quote, index) => (
                  <p key={`consumer-evidence-${index}`}>- {quote}</p>
                ))}
              </div>
            </div>
          ) : null}
        </article>

        <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
            2 · {renderModuleLabel("user_experience")}
          </div>
          <p className="mt-4 text-sm leading-7 text-soft">{userExperience.summary}</p>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <div className="rounded-card border border-line bg-[#f8fffc] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">正向反馈</div>
              <div className="mt-3 space-y-3">
                {userExperience.positive.map((row, index) => (
                  <div key={`positive-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                    <div className="text-sm font-semibold text-ink">
                      {renderValue(row.tag || row.label || `亮点 ${index + 1}`)}
                    </div>
                    <div className="mt-2 text-sm leading-7 text-soft">
                      {renderValue(row.reason || row.detail || row.pct)}
                    </div>
                  </div>
                ))}
                {userExperience.positive.length === 0 ? (
                  <div className="text-sm leading-7 text-soft">暂无稳定正向反馈。</div>
                ) : null}
              </div>
            </div>
            <div className="rounded-card border border-line bg-[#fff8f9] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">负向反馈</div>
              <div className="mt-3 space-y-3">
                {userExperience.negative.map((row, index) => (
                  <div key={`negative-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                    <div className="text-sm font-semibold text-ink">
                      {renderValue(row.tag || row.label || `问题 ${index + 1}`)}
                    </div>
                    <div className="mt-2 text-sm leading-7 text-soft">
                      {renderValue(row.reason || row.detail || row.pct)}
                    </div>
                  </div>
                ))}
                {userExperience.negative.length === 0 ? (
                  <div className="text-sm leading-7 text-soft">暂无稳定负向反馈。</div>
                ) : null}
              </div>
            </div>
          </div>
        </article>

        <div className="grid gap-5 xl:grid-cols-2">
          <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
            <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
              3 · {renderModuleLabel("purchase_motives")}
            </div>
            <p className="mt-4 text-sm leading-7 text-soft">{purchaseMotives.summary}</p>
            <div className="mt-5 space-y-3">
              {purchaseMotives.rows.map((row, index) => (
                <div key={`motive-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                  <div className="text-sm font-semibold text-ink">
                    {renderValue(row.label || row.tag || `动机 ${index + 1}`)}
                  </div>
                  <div className="mt-2 text-sm leading-7 text-soft">
                    {renderValue(row.detail || row.reason || row.summary || row.value)}
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
            <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
              4 · {renderModuleLabel("unmet_needs")}
            </div>
            <p className="mt-4 text-sm leading-7 text-soft">{unmetNeeds.summary}</p>
            <div className="mt-5 space-y-3">
              {unmetNeeds.rows.map((row, index) => (
                <div key={`need-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                  <div className="text-sm font-semibold text-ink">
                    {renderValue(row.label || row.tag || `需求 ${index + 1}`)}
                  </div>
                  <div className="mt-2 text-sm leading-7 text-soft">
                    {renderValue(row.detail || row.reason || row.summary || row.value)}
                  </div>
                </div>
              ))}
            </div>
          </article>
        </div>

        <article className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
          <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
            5 · {renderModuleLabel("recommendations")}
          </div>
          <p className="mt-4 text-sm leading-7 text-soft">{recommendations.summary}</p>
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {recommendations.rows.map((row, index) => (
              <div key={`recommend-${index}`} className="rounded-card border border-line bg-white px-4 py-4">
                <div className="text-sm font-semibold text-ink">
                  {renderValue(row.label || row.tag || row.title || `建议 ${index + 1}`)}
                </div>
                <div className="mt-2 text-sm leading-7 text-soft">
                  {renderValue(row.detail || row.reason || row.summary || row.value)}
                </div>
              </div>
            ))}
          </div>
          {recommendations.evidence.length > 0 ? (
            <div className="mt-5 rounded-card border border-line bg-[#fffafc] p-4">
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                建议依据
              </div>
              <div className="mt-3 space-y-2 text-sm leading-7 text-ink">
                {recommendations.evidence.map((quote, index) => (
                  <p key={`recommend-evidence-${index}`}>- {quote}</p>
                ))}
              </div>
            </div>
          ) : null}
        </article>
      </section>

      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
          6 · 评论原文
        </div>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="font-heading text-2xl font-extrabold tracking-[-0.04em] text-ink">
              评论原文
            </h3>
            <p className="mt-2 text-sm leading-7 text-soft">
              结果页保留原始评论明细，便于从结论回到证据。
            </p>
          </div>
          <Link
            href={`/analysis/compare?product_id=${encodeURIComponent(payload.session.product_id)}`}
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
          >
            去看对比
          </Link>
        </div>

        <div className="mt-5 space-y-3">
          {payload.comments.length > 0 ? (
            payload.comments.slice(0, 24).map((comment, index) => (
              <div key={String(comment.id ?? index)} className="rounded-card border border-line bg-white px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.12em] text-soft">
                  {renderValue(comment.date, "无日期")} · {renderValue(comment.sentiment, "未分析")}
                </div>
                <div className="mt-2 text-sm leading-7 text-ink">
                  {renderValue(comment.content, "")}
                </div>
              </div>
            ))
          ) : (
            <div className="rounded-card border border-dashed border-line bg-[#fffafb] px-5 py-6 text-sm leading-7 text-soft">
              当前批次没有可展示的评论原文。
            </div>
          )}
        </div>
      </section>
    </AppShell>
  );
}
