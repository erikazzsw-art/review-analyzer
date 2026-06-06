"""欢迎页面。"""

from __future__ import annotations

from textwrap import dedent

import streamlit as st

from review_analyzer.i18n import pick, t


def _render_html_block(content: str) -> None:
    st.markdown(dedent(content).strip(), unsafe_allow_html=True)


def render_landing_page() -> None:
    raw_variant = str(st.session_state.get("landing_preview_variant", "current"))
    if st.session_state.get("force_public_preview") and raw_variant == "current":
        preview_variant = "current"
    else:
        preview_variant = "refresh"
    _render_preview_variant_switcher(preview_variant)
    if preview_variant == "refresh":
        _render_refresh_landing_page()
        return
    _render_current_landing_page()


def _render_current_landing_page() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        .stApp { background: linear-gradient(180deg, #fffaf8 0%, #fff6f7 52%, #f8f4ff 100%); }
        section[data-testid="stMain"] > div { padding: 0 !important; max-width: 100% !important; }

        .landing-shell {
            max-width: 1180px;
            margin: 0 auto;
            padding: 0 24px 64px;
            font-family: 'Inter', system-ui, sans-serif;
            color: #25212a;
        }
        .landing-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 24px 0 18px;
        }
        .landing-brand {
            display: inline-flex;
            align-items: center;
            gap: 12px;
        }
        .landing-mark {
            width: 42px;
            height: 42px;
            border-radius: 16px;
            background: linear-gradient(135deg, #f36f8f, #8d7be8);
            color: #ffffff;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-weight: 800;
            font-size: 16px;
            box-shadow: 0 16px 34px rgba(121, 88, 137, 0.18);
        }
        .landing-brand-copy strong {
            display: block;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 20px;
            letter-spacing: -0.02em;
        }
        .landing-brand-copy span {
            display: block;
            color: #7b7384;
            font-size: 13px;
            margin-top: 2px;
        }
        .landing-note {
            display: inline-flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid #ebe4ee;
            color: #7b7384;
            font-size: 13px;
        }
        .landing-hero-grid,
        .landing-trust-grid,
        .landing-flow-grid {
            display: grid;
            gap: 18px;
        }
        .landing-hero-grid {
            grid-template-columns: minmax(0, 1.04fr) minmax(340px, 0.96fr);
            align-items: stretch;
            margin-top: 8px;
        }
        .landing-card,
        .landing-cta-card {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid #ebe4ee;
            border-radius: 28px;
            box-shadow: 0 20px 52px rgba(96, 63, 88, 0.10);
            backdrop-filter: blur(10px);
        }
        .landing-hero-copy {
            padding: 34px 34px 28px;
            position: relative;
            overflow: hidden;
        }
        .landing-hero-copy::after {
            content: "";
            position: absolute;
            right: -60px;
            top: -80px;
            width: 220px;
            height: 220px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(243, 111, 143, 0.18) 0%, rgba(243, 111, 143, 0) 70%);
            pointer-events: none;
        }
        .landing-eyebrow {
            display: inline-flex;
            align-items: center;
            padding: 7px 13px;
            border-radius: 999px;
            background: #fff1f5;
            color: #d94d72;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 16px;
        }
        .landing-hero-copy h1 {
            margin: 0;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 48px;
            line-height: 1.08;
            letter-spacing: -0.03em;
            color: #25212a;
        }
        .landing-hero-copy p {
            margin: 16px 0 0;
            max-width: 580px;
            color: #6f6877;
            font-size: 15px;
            line-height: 1.78;
        }
        .landing-points {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 22px;
        }
        .landing-point {
            padding: 14px 16px;
            border-radius: 18px;
            background: #fff8fb;
            border: 1px solid #f1e3eb;
        }
        .landing-point strong {
            display: block;
            font-size: 14px;
            margin-bottom: 4px;
            color: #25212a;
        }
        .landing-point span {
            display: block;
            font-size: 13px;
            line-height: 1.65;
            color: #7b7384;
        }
        .landing-hero-preview {
            padding: 24px;
            background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(252,246,251,0.98) 100%);
            display: grid;
            gap: 12px;
        }
        .landing-preview-top {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }
        .landing-metric,
        .landing-preview-item,
        .landing-trust-item,
        .landing-flow-item {
            border-radius: 20px;
            background: #ffffff;
            border: 1px solid #ebe4ee;
        }
        .landing-metric {
            padding: 18px 18px 16px;
        }
        .landing-metric span {
            display: block;
            font-size: 12px;
            color: #8d8598;
            margin-bottom: 8px;
        }
        .landing-metric strong {
            display: block;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 28px;
            letter-spacing: -0.03em;
            color: #25212a;
        }
        .landing-strip {
            display: block;
            height: 6px;
            border-radius: 999px;
            margin-top: 10px;
        }
        .landing-strip.green { background: linear-gradient(90deg, #4fb99f, #8fd5bf); width: 78%; }
        .landing-strip.pink { background: linear-gradient(90deg, #f36f8f, #f8a1b7); width: 43%; }
        .landing-preview-stack {
            display: grid;
            gap: 12px;
        }
        .landing-preview-item {
            padding: 16px 18px;
        }
        .landing-preview-item strong,
        .landing-trust-item strong,
        .landing-flow-item strong {
            display: block;
            font-size: 14px;
            color: #25212a;
            margin-bottom: 6px;
        }
        .landing-preview-item p,
        .landing-trust-item p,
        .landing-flow-item p {
            margin: 0;
            font-size: 13px;
            line-height: 1.7;
            color: #6f6877;
        }
        .landing-section {
            margin-top: 24px;
        }
        .landing-section-header {
            padding: 0 4px;
            margin-bottom: 16px;
        }
        .landing-section-header strong {
            display: block;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 30px;
            letter-spacing: -0.03em;
            color: #25212a;
        }
        .landing-section-header span {
            display: block;
            margin-top: 8px;
            max-width: 680px;
            font-size: 14px;
            line-height: 1.75;
            color: #6f6877;
        }
        .landing-surface {
            padding: 26px;
        }
        .landing-trust-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        .landing-flow-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .landing-trust-item,
        .landing-flow-item {
            padding: 20px 20px 18px;
            background: linear-gradient(180deg, #ffffff 0%, #fff8fb 100%);
        }
        .landing-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            border-radius: 12px;
            margin-bottom: 14px;
            font-size: 12px;
            font-weight: 800;
            color: #ffffff;
            font-family: 'Montserrat', system-ui, sans-serif;
            background: linear-gradient(135deg, #f36f8f, #8d7be8);
        }
        .landing-cta-card {
            margin-top: 24px;
            padding: 32px 30px 26px;
            background: linear-gradient(135deg, #25212a 0%, #3d3148 58%, #57416b 100%);
            color: #ffffff;
        }
        .landing-cta-card strong {
            display: block;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 30px;
            letter-spacing: -0.03em;
            margin-bottom: 10px;
        }
        .landing-cta-card p {
            margin: 0;
            max-width: 620px;
            color: rgba(255, 255, 255, 0.78);
            font-size: 14px;
            line-height: 1.72;
        }
        @media (max-width: 980px) {
            .landing-hero-grid,
            .landing-trust-grid,
            .landing-flow-grid,
            .landing-points,
            .landing-preview-top {
                grid-template-columns: 1fr;
            }
            .landing-topbar {
                align-items: flex-start;
                flex-direction: column;
            }
            .landing-hero-copy h1 {
                font-size: 36px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _render_html_block(
        pick(
            """
            <div class="landing-shell">
                <div class="landing-topbar">
                    <div class="landing-brand">
                        <div class="landing-mark">C</div>
                        <div class="landing-brand-copy">
                            <strong>ClueAI</strong>
                            <span>把评论分析、动作跟进和复盘验证串成一条工作流</span>
                        </div>
                    </div>
                    <div class="landing-note">当前欢迎页 · 本地对比基线</div>
                </div>

                <div class="landing-hero-grid">
                    <div class="landing-card landing-hero-copy">
                        <div class="landing-eyebrow">跨境卖家的评论工作台</div>
                        <h1>从海量评论里，直接看到<br>今天该处理什么。</h1>
                        <p>
                            上传评论后，ClueAI 会帮你提炼核心问题、核心亮点、对比变化、团队动作和复盘线索。
                            你不用再在表格、截图和聊天记录之间来回切换。
                        </p>
                        <div class="landing-points">
                            <div class="landing-point">
                                <strong>上传即进入主链路</strong>
                                <span>工作目的、产品组、变体绑定和结果页跳转已经连起来。</span>
                            </div>
                            <div class="landing-point">
                                <strong>从问题直接变成动作</strong>
                                <span>TOP 问题可以一键进入行动中心，再进入复盘追踪。</span>
                            </div>
                            <div class="landing-point">
                                <strong>适合本地演示验收</strong>
                                <span>欢迎页、登录页和系统内页已经收成同一套 V2 语言。</span>
                            </div>
                        </div>
                    </div>

                    <div class="landing-card landing-hero-preview">
                        <div class="landing-preview-top">
                            <div class="landing-metric">
                                <span>正面率</span>
                                <strong>78%</strong>
                                <i class="landing-strip green"></i>
                            </div>
                            <div class="landing-metric">
                                <span>高风险问题</span>
                                <strong>12%</strong>
                                <i class="landing-strip pink"></i>
                            </div>
                        </div>
                        <div class="landing-preview-stack">
                            <div class="landing-preview-item">
                                <strong>今日工作台</strong>
                                <p>优先处理高风险 SKU、待复盘事项和最近上传批次，而不是先看功能目录。</p>
                            </div>
                            <div class="landing-preview-item">
                                <strong>评论分析 → 行动中心</strong>
                                <p>从评论上传、结果洞察到团队动作分发，路径已经收敛为一条清晰主链路。</p>
                            </div>
                            <div class="landing-preview-item">
                                <strong>对比分析 → AI 总结</strong>
                                <p>支持多产品、变体、版本和时间对比，并补充一句话结论、风险提醒和建议动作。</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """,
            """
            <div class="landing-shell">
                <div class="landing-topbar">
                    <div class="landing-brand">
                        <div class="landing-mark">C</div>
                        <div class="landing-brand-copy">
                            <strong>ClueAI</strong>
                            <span>Turn review analysis, team actions, and follow-up validation into one workflow.</span>
                        </div>
                    </div>
                    <div class="landing-note">Current landing · local comparison baseline</div>
                </div>

                <div class="landing-hero-grid">
                    <div class="landing-card landing-hero-copy">
                        <div class="landing-eyebrow">A review workspace for cross-border sellers</div>
                        <h1>See what needs your attention<br>today, directly from your reviews.</h1>
                        <p>
                            After you upload reviews, ClueAI helps surface the core issues, key highlights, comparison changes,
                            team actions, and follow-up clues, so you no longer have to jump between spreadsheets,
                            screenshots, and chat threads.
                        </p>
                        <div class="landing-points">
                            <div class="landing-point">
                                <strong>Upload straight into the main flow</strong>
                                <span>Work purpose, product groups, variant binding, and the results page are already connected.</span>
                            </div>
                            <div class="landing-point">
                                <strong>Turn issues into actions fast</strong>
                                <span>Top issues can move directly into the Action Center and then into Follow-up Tracking.</span>
                            </div>
                            <div class="landing-point">
                                <strong>Better for local review</strong>
                                <span>The landing page, login flow, and in-app pages now share the same V2 language.</span>
                            </div>
                        </div>
                    </div>

                    <div class="landing-card landing-hero-preview">
                        <div class="landing-preview-top">
                            <div class="landing-metric">
                                <span>Positive Rate</span>
                                <strong>78%</strong>
                                <i class="landing-strip green"></i>
                            </div>
                            <div class="landing-metric">
                                <span>High-Risk Issues</span>
                                <strong>12%</strong>
                                <i class="landing-strip pink"></i>
                            </div>
                        </div>
                        <div class="landing-preview-stack">
                            <div class="landing-preview-item">
                                <strong>Today's Workspace</strong>
                                <p>Focus first on high-risk SKUs, pending follow-ups, and recent uploads instead of starting from a feature list.</p>
                            </div>
                            <div class="landing-preview-item">
                                <strong>Review Analysis → Action Center</strong>
                                <p>From uploads and insights to team action distribution, the path is now one clear main workflow.</p>
                            </div>
                            <div class="landing-preview-item">
                                <strong>Compare → AI Summary</strong>
                                <p>Compare products, variants, versions, and time periods, then get a one-line takeaway, risk note, and next-step suggestion.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """,
        )
    )

    _render_workspace_return()
    _render_primary_actions("landing_current_primary")

    _render_html_block(
        pick(
            """
            <div class="landing-shell landing-section">
                <div class="landing-section-header">
                    <strong>系统现在更像一个完整产品，而不是几个页面拼接。</strong>
                    <span>欢迎页先帮你建立预期，进入系统后再沿着工作台、上传、结果、动作和复盘继续往下走。</span>
                </div>
                <div class="landing-card landing-surface">
                    <div class="landing-trust-grid">
                        <div class="landing-trust-item">
                            <div class="landing-badge">01</div>
                            <strong>工作流优先</strong>
                            <p>默认导航收敛成高频路径，新用户更容易按顺序完成一轮真实工作。</p>
                        </div>
                        <div class="landing-trust-item">
                            <div class="landing-badge">02</div>
                            <strong>产品资产沉淀</strong>
                            <p>产品组、变体 SKU、批次和历史评论会逐步沉淀，不再只围绕一次上传看结果。</p>
                        </div>
                        <div class="landing-trust-item">
                            <div class="landing-badge">03</div>
                            <strong>动作和复盘闭环</strong>
                            <p>发现问题后直接分给运营、产研或质检，再继续追踪是否真的改善。</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            """
            <div class="landing-shell landing-section">
                <div class="landing-section-header">
                    <strong>The system now feels like one product, not a stack of disconnected pages.</strong>
                    <span>The landing page sets expectations first, then the app carries you through workspace, uploads, results, actions, and follow-ups.</span>
                </div>
                <div class="landing-card landing-surface">
                    <div class="landing-trust-grid">
                        <div class="landing-trust-item">
                            <div class="landing-badge">01</div>
                            <strong>Workflow first</strong>
                            <p>The default navigation is reduced to the high-frequency path so one real work cycle is easier to complete.</p>
                        </div>
                        <div class="landing-trust-item">
                            <div class="landing-badge">02</div>
                            <strong>Product assets accumulate</strong>
                            <p>Product groups, variant SKUs, sessions, and historical reviews keep building instead of being tied to one upload.</p>
                        </div>
                        <div class="landing-trust-item">
                            <div class="landing-badge">03</div>
                            <strong>Action and follow-up loop</strong>
                            <p>Once an issue is found, it can move directly to operations, product, or QA, then be tracked until improvement is confirmed.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
        )
    )

    _render_html_block(
        pick(
            """
            <div class="landing-shell landing-section">
                <div class="landing-section-header">
                    <strong>你可以按这几条路径开始体验。</strong>
                    <span>欢迎页不只是介绍页，也提前告诉你系统里最典型的 4 条使用路径。</span>
                </div>
                <div class="landing-card landing-surface">
                    <div class="landing-flow-grid">
                        <div class="landing-flow-item">
                            <div class="landing-badge">1</div>
                            <strong>开始新分析</strong>
                            <p>上传评论，绑定产品组和工作目的，然后自动进入分析结果页继续看问题和亮点。</p>
                        </div>
                        <div class="landing-flow-item">
                            <div class="landing-badge">2</div>
                            <strong>推进团队事项</strong>
                            <p>从结果页把 TOP 问题变成 action item，分配角色、设置状态并进入行动中心。</p>
                        </div>
                        <div class="landing-flow-item">
                            <div class="landing-badge">3</div>
                            <strong>判断改进是否有效</strong>
                            <p>把待复盘事项升级成 tracker，填写评论范围、当前占比和最终结论。</p>
                        </div>
                        <div class="landing-flow-item">
                            <div class="landing-badge">4</div>
                            <strong>进入高级入口</strong>
                            <p>需要做对比、查历史、问评论或调推送规则时，直接进入对应一级导航继续展开。</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            """
            <div class="landing-shell landing-section">
                <div class="landing-section-header">
                    <strong>You can start with these typical paths.</strong>
                    <span>The landing page is no longer just an intro page. It also shows the most common ways to use the system.</span>
                </div>
                <div class="landing-card landing-surface">
                    <div class="landing-flow-grid">
                        <div class="landing-flow-item">
                            <div class="landing-badge">1</div>
                            <strong>Start a new analysis</strong>
                            <p>Upload reviews, bind a product group and work purpose, then continue automatically into the results page.</p>
                        </div>
                        <div class="landing-flow-item">
                            <div class="landing-badge">2</div>
                            <strong>Move team tasks forward</strong>
                            <p>Turn top issues into action items, assign owners, update status, and continue in the Action Center.</p>
                        </div>
                        <div class="landing-flow-item">
                            <div class="landing-badge">3</div>
                            <strong>Check whether improvements worked</strong>
                            <p>Promote pending items into trackers, then record scope, current rate, and final conclusion.</p>
                        </div>
                        <div class="landing-flow-item">
                            <div class="landing-badge">4</div>
                            <strong>Open advanced entry points</strong>
                            <p>When you need comparison, history, review Q&A, or notification rules, continue from the related first-level page.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
        )
    )

    _render_html_block(
        pick(
            """
            <div class="landing-shell">
                <div class="landing-cta-card">
                    <strong>现在就开始看你的评论，到底在提醒你什么。</strong>
                    <p>你可以先用试用入口熟悉流程，也可以直接注册账号进入完整工作台。下面的按钮逻辑保持不变，只是外观已经和系统内统一了。</p>
                </div>
            </div>
            """,
            """
            <div class="landing-shell">
                <div class="landing-cta-card">
                    <strong>Start exploring what your reviews are really telling you.</strong>
                    <p>You can try the flow first, or create an account and move directly into the full workspace. The button logic stays the same while the experience remains aligned with the product.</p>
                </div>
            </div>
            """,
        )
    )

    _render_primary_actions("landing_current_footer")


def _render_refresh_landing_page() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        .stApp { background: linear-gradient(180deg, #fffaf8 0%, #fff6f7 50%, #f8f4ff 100%); }
        section[data-testid="stMain"] > div { padding: 0 !important; max-width: 100% !important; }

        .refresh-shell {
            max-width: 1180px;
            margin: 0 auto;
            padding: 0 24px 72px;
            font-family: 'Inter', system-ui, sans-serif;
            color: #25212a;
        }
        .refresh-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 24px 0 18px;
        }
        .refresh-brand {
            display: inline-flex;
            align-items: center;
            gap: 12px;
        }
        .refresh-mark {
            width: 42px;
            height: 42px;
            border-radius: 16px;
            background: linear-gradient(135deg, #f36f8f, #8d7be8);
            color: #ffffff;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-weight: 800;
            font-size: 16px;
            box-shadow: 0 16px 34px rgba(121, 88, 137, 0.18);
        }
        .refresh-brand-copy strong {
            display: block;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 20px;
            letter-spacing: -0.02em;
        }
        .refresh-brand-copy span {
            display: block;
            color: #7b7384;
            font-size: 13px;
            margin-top: 2px;
        }
        .refresh-note {
            display: inline-flex;
            align-items: center;
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid #ebe4ee;
            color: #7b7384;
            font-size: 13px;
        }
        .refresh-hero {
            display: grid;
            grid-template-columns: minmax(0, 0.98fr) minmax(0, 1.02fr);
            gap: 22px;
            align-items: stretch;
            margin-top: 6px;
        }
        .refresh-card,
        .refresh-cta {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid #ebe4ee;
            border-radius: 30px;
            box-shadow: 0 22px 56px rgba(96, 63, 88, 0.10);
            backdrop-filter: blur(10px);
        }
        .refresh-copy {
            padding: 38px 36px 30px;
            position: relative;
            overflow: hidden;
        }
        .refresh-copy::before {
            content: "";
            position: absolute;
            inset: auto auto -40px -40px;
            width: 180px;
            height: 180px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(141, 123, 232, 0.16) 0%, rgba(141, 123, 232, 0) 72%);
            pointer-events: none;
        }
        .refresh-eyebrow {
            display: inline-flex;
            align-items: center;
            padding: 7px 13px;
            border-radius: 999px;
            background: #fff1f5;
            color: #d94d72;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 18px;
        }
        .refresh-copy h1 {
            margin: 0;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 52px;
            line-height: 1.04;
            letter-spacing: -0.04em;
            color: #25212a;
            max-width: 560px;
        }
        .refresh-copy p {
            margin: 18px 0 0;
            max-width: 560px;
            color: #6f6877;
            font-size: 15px;
            line-height: 1.82;
        }
        .refresh-hero-tags {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 24px;
        }
        .refresh-tag {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            border-radius: 999px;
            background: #ffffff;
            border: 1px solid #ece4ef;
            color: #5f5768;
            font-size: 13px;
            box-shadow: 0 10px 26px rgba(96, 63, 88, 0.06);
        }
        .refresh-tag i {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: linear-gradient(135deg, #f36f8f, #8d7be8);
            display: inline-block;
        }
        .refresh-shot {
            padding: 24px;
            background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(252,246,251,0.98) 100%);
            display: grid;
            gap: 14px;
        }
        .refresh-window {
            border-radius: 26px;
            border: 1px solid #e9e2ee;
            background: linear-gradient(180deg, #fffdfd 0%, #fff7fb 100%);
            padding: 18px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
        }
        .refresh-window-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 16px;
        }
        .refresh-dots {
            display: inline-flex;
            gap: 6px;
        }
        .refresh-dots i {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: #efdde4;
            display: inline-block;
        }
        .refresh-window-top span {
            color: #8d8598;
            font-size: 12px;
        }
        .refresh-shot-grid {
            display: grid;
            grid-template-columns: 1.15fr 0.85fr;
            gap: 14px;
        }
        .refresh-shot-panel,
        .refresh-shot-side,
        .refresh-mini,
        .refresh-line-item,
        .refresh-callout {
            background: #ffffff;
            border: 1px solid #ebe4ee;
            border-radius: 22px;
        }
        .refresh-shot-panel {
            padding: 18px;
            display: grid;
            gap: 14px;
        }
        .refresh-panel-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
        }
        .refresh-panel-head strong {
            display: block;
            font-size: 15px;
            color: #25212a;
            margin-bottom: 4px;
        }
        .refresh-panel-head span {
            display: block;
            font-size: 12px;
            color: #8d8598;
        }
        .refresh-badge {
            display: inline-flex;
            align-items: center;
            padding: 7px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            background: #fff1f5;
            color: #d94d72;
        }
        .refresh-metrics {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
        }
        .refresh-mini {
            padding: 14px;
        }
        .refresh-mini span {
            display: block;
            color: #8d8598;
            font-size: 11px;
            margin-bottom: 7px;
        }
        .refresh-mini strong {
            display: block;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 26px;
            letter-spacing: -0.03em;
            color: #25212a;
        }
        .refresh-mini em {
            display: block;
            margin-top: 8px;
            font-size: 11px;
            color: #6f6877;
            font-style: normal;
        }
        .refresh-list {
            display: grid;
            gap: 10px;
        }
        .refresh-line-item {
            padding: 14px 15px;
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 14px;
        }
        .refresh-line-item strong {
            display: block;
            font-size: 13px;
            color: #25212a;
            margin-bottom: 4px;
        }
        .refresh-line-item span {
            display: block;
            font-size: 12px;
            line-height: 1.6;
            color: #6f6877;
        }
        .refresh-line-mark {
            min-width: 58px;
            padding: 6px 8px;
            border-radius: 999px;
            text-align: center;
            font-size: 11px;
            font-weight: 700;
        }
        .refresh-line-mark.pink {
            background: #fff0f5;
            color: #d94d72;
        }
        .refresh-line-mark.green {
            background: #eef9f4;
            color: #359f84;
        }
        .refresh-shot-side {
            padding: 16px;
            display: grid;
            gap: 10px;
            align-content: start;
        }
        .refresh-side-title {
            font-size: 13px;
            font-weight: 700;
            color: #25212a;
        }
        .refresh-side-text {
            font-size: 12px;
            line-height: 1.7;
            color: #6f6877;
        }
        .refresh-side-bar {
            height: 8px;
            border-radius: 999px;
            background: #f3ebf5;
            overflow: hidden;
        }
        .refresh-side-bar i {
            display: block;
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #f36f8f, #8d7be8);
        }
        .refresh-callouts {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
        }
        .refresh-callout {
            padding: 16px 16px 14px;
            background: linear-gradient(180deg, #ffffff 0%, #fff8fb 100%);
        }
        .refresh-callout strong {
            display: block;
            font-size: 13px;
            color: #25212a;
            margin-bottom: 6px;
        }
        .refresh-callout p {
            margin: 0;
            font-size: 12px;
            line-height: 1.72;
            color: #6f6877;
        }
        .refresh-section {
            margin-top: 28px;
        }
        .refresh-section-head {
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 18px;
            margin-bottom: 16px;
            padding: 0 4px;
        }
        .refresh-section-head strong {
            display: block;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 30px;
            line-height: 1.1;
            letter-spacing: -0.03em;
            color: #25212a;
        }
        .refresh-section-head span {
            display: block;
            margin-top: 8px;
            max-width: 720px;
            font-size: 14px;
            line-height: 1.78;
            color: #6f6877;
        }
        .refresh-surface {
            padding: 26px;
        }
        .refresh-value-grid,
        .refresh-diff-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
        }
        .refresh-value-item,
        .refresh-diff-item {
            border-radius: 24px;
            border: 1px solid #eee5f1;
            background: linear-gradient(180deg, #ffffff 0%, #fff8fb 100%);
            padding: 22px 20px 18px;
        }
        .refresh-index {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            border-radius: 14px;
            background: linear-gradient(135deg, #f36f8f, #8d7be8);
            color: #ffffff;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 12px;
            font-weight: 800;
            margin-bottom: 14px;
        }
        .refresh-value-item strong,
        .refresh-diff-item strong {
            display: block;
            font-size: 16px;
            color: #25212a;
            margin-bottom: 8px;
        }
        .refresh-value-item p,
        .refresh-diff-item p {
            margin: 0;
            font-size: 13px;
            line-height: 1.72;
            color: #6f6877;
        }
        .refresh-cta {
            margin-top: 28px;
            padding: 34px 30px 28px;
            background: linear-gradient(135deg, #25212a 0%, #3c3148 58%, #58426e 100%);
            color: #ffffff;
        }
        .refresh-cta strong {
            display: block;
            font-family: 'Montserrat', system-ui, sans-serif;
            font-size: 32px;
            letter-spacing: -0.03em;
            margin-bottom: 10px;
        }
        .refresh-cta p {
            margin: 0;
            max-width: 660px;
            color: rgba(255, 255, 255, 0.78);
            font-size: 14px;
            line-height: 1.76;
        }
        @media (max-width: 980px) {
            .refresh-hero,
            .refresh-shot-grid,
            .refresh-callouts,
            .refresh-value-grid,
            .refresh-diff-grid,
            .refresh-metrics {
                grid-template-columns: 1fr;
            }
            .refresh-topbar,
            .refresh-section-head {
                align-items: flex-start;
                flex-direction: column;
            }
            .refresh-copy h1 {
                font-size: 38px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _render_html_block(
        pick(
            """
            <div class="refresh-shell">
                <div class="refresh-topbar">
                    <div class="refresh-brand">
                        <div class="refresh-mark">C</div>
                        <div class="refresh-brand-copy">
                            <strong>ClueAI</strong>
                            <span>把评论分析、动作跟进和复盘验证串成一条工作流</span>
                        </div>
                    </div>
                    <div class="refresh-note">新版欢迎页预览 · 先看本地样子</div>
                </div>

                <div class="refresh-hero">
                    <div class="refresh-card refresh-copy">
                        <div class="refresh-eyebrow">跨境运营负责人的评论决策首页</div>
                        <h1>从海量评论里，直接看到今天该先处理什么。</h1>
                        <p>
                            ClueAI 不只是把评论做成情感统计，而是把高风险问题、团队动作和后续复盘收成一条清晰链路。
                            上传后先看到重点，再决定谁来处理、什么时候验证是否真的改善。
                        </p>
                        <div class="refresh-hero-tags">
                            <span class="refresh-tag"><i></i> 发现高风险问题</span>
                            <span class="refresh-tag"><i></i> 把问题转成动作</span>
                            <span class="refresh-tag"><i></i> 用后续评论验证结果</span>
                        </div>
                    </div>

                    <div class="refresh-card refresh-shot">
                        <div class="refresh-window">
                            <div class="refresh-window-top">
                                <div class="refresh-dots"><i></i><i></i><i></i></div>
                                <span>ClueAI · Review Analysis Workspace</span>
                            </div>
                            <div class="refresh-shot-grid">
                                <div class="refresh-shot-panel">
                                    <div class="refresh-panel-head">
                                        <div>
                                            <strong>今日评论工作台</strong>
                                            <span>最近 30 天 · Bed Frame Collection</span>
                                        </div>
                                        <div class="refresh-badge">优先处理</div>
                                    </div>
                                    <div class="refresh-metrics">
                                        <div class="refresh-mini">
                                            <span>正面率</span>
                                            <strong>78%</strong>
                                            <em>本周期稳定</em>
                                        </div>
                                        <div class="refresh-mini">
                                            <span>高风险问题</span>
                                            <strong>12%</strong>
                                            <em>包装问题上升</em>
                                        </div>
                                        <div class="refresh-mini">
                                            <span>待复盘事项</span>
                                            <strong>3</strong>
                                            <em>2 项本周到期</em>
                                        </div>
                                    </div>
                                    <div class="refresh-list">
                                        <div class="refresh-line-item">
                                            <div>
                                                <strong>包装破损</strong>
                                                <span>差评中占比 32%，集中在最近两批次，建议先进入质检动作。</span>
                                            </div>
                                            <div class="refresh-line-mark pink">高风险</div>
                                        </div>
                                        <div class="refresh-line-item">
                                            <div>
                                                <strong>安装误解</strong>
                                                <span>用户频繁误装到木墙场景，Listing 说明仍需要补强。</span>
                                            </div>
                                            <div class="refresh-line-mark green">可优化</div>
                                        </div>
                                    </div>
                                </div>
                                <div class="refresh-shot-side">
                                    <div class="refresh-side-title">行动中心</div>
                                    <div class="refresh-side-text">TOP 问题可直接生成团队事项，并写入预计复盘时间。</div>
                                    <div class="refresh-side-bar"><i style="width:72%;"></i></div>
                                    <div class="refresh-side-title">版本对比</div>
                                    <div class="refresh-side-text">V2 安装问题下降，包装问题开始替代成为新的主风险。</div>
                                    <div class="refresh-side-bar"><i style="width:54%;"></i></div>
                                    <div class="refresh-side-title">复盘验证</div>
                                    <div class="refresh-side-text">包装加固后的评论范围已准备好，可直接进入跟踪判断是否改善。</div>
                                    <div class="refresh-side-bar"><i style="width:61%;"></i></div>
                                </div>
                            </div>
                        </div>
                        <div class="refresh-callouts">
                            <div class="refresh-callout">
                                <strong>TOP 问题不是孤立数字</strong>
                                <p>每个高频问题都应该连到负责人、处理动作和复盘节点，而不是停在一张报告里。</p>
                            </div>
                            <div class="refresh-callout">
                                <strong>截图像真实产品，而不是概念图</strong>
                                <p>欢迎页先用接近真实后台的视觉建立信任，再用短文案解释你能拿到什么结果。</p>
                            </div>
                            <div class="refresh-callout">
                                <strong>先讲今天该做什么</strong>
                                <p>首页优先传达决策价值，不把用户带进复杂功能目录和长篇功能说明。</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """,
            """
            <div class="refresh-shell">
                <div class="refresh-topbar">
                    <div class="refresh-brand">
                        <div class="refresh-mark">C</div>
                        <div class="refresh-brand-copy">
                            <strong>ClueAI</strong>
                            <span>Turn review analysis, team actions, and follow-up validation into one workflow.</span>
                        </div>
                    </div>
                    <div class="refresh-note">New landing preview · local review first</div>
                </div>

                <div class="refresh-hero">
                    <div class="refresh-card refresh-copy">
                        <div class="refresh-eyebrow">A decision-ready homepage for cross-border operators</div>
                        <h1>See what deserves your attention first, directly from your reviews.</h1>
                        <p>
                            ClueAI does more than summarize review sentiment. It turns rising issues, team actions,
                            and follow-up validation into one clear operating loop, so the next step is visible right after upload.
                        </p>
                        <div class="refresh-hero-tags">
                            <span class="refresh-tag"><i></i> Spot high-risk issues</span>
                            <span class="refresh-tag"><i></i> Turn findings into actions</span>
                            <span class="refresh-tag"><i></i> Validate changes with later reviews</span>
                        </div>
                    </div>

                    <div class="refresh-card refresh-shot">
                        <div class="refresh-window">
                            <div class="refresh-window-top">
                                <div class="refresh-dots"><i></i><i></i><i></i></div>
                                <span>ClueAI · Review Analysis Workspace</span>
                            </div>
                            <div class="refresh-shot-grid">
                                <div class="refresh-shot-panel">
                                    <div class="refresh-panel-head">
                                        <div>
                                            <strong>Today's review workspace</strong>
                                            <span>Last 30 days · Bed Frame Collection</span>
                                        </div>
                                        <div class="refresh-badge">Priority first</div>
                                    </div>
                                    <div class="refresh-metrics">
                                        <div class="refresh-mini">
                                            <span>Positive Rate</span>
                                            <strong>78%</strong>
                                            <em>Stable this cycle</em>
                                        </div>
                                        <div class="refresh-mini">
                                            <span>High-Risk Issues</span>
                                            <strong>12%</strong>
                                            <em>Packaging complaints rising</em>
                                        </div>
                                        <div class="refresh-mini">
                                            <span>Open Follow-ups</span>
                                            <strong>3</strong>
                                            <em>2 due this week</em>
                                        </div>
                                    </div>
                                    <div class="refresh-list">
                                        <div class="refresh-line-item">
                                            <div>
                                                <strong>Packaging damage</strong>
                                                <span>32% of negative reviews mention it, concentrated in the latest batches. QA action should come first.</span>
                                            </div>
                                            <div class="refresh-line-mark pink">High Risk</div>
                                        </div>
                                        <div class="refresh-line-item">
                                            <div>
                                                <strong>Installation misunderstanding</strong>
                                                <span>Users still install it on the wrong surface, so the listing copy needs stronger guidance.</span>
                                            </div>
                                            <div class="refresh-line-mark green">Fixable</div>
                                        </div>
                                    </div>
                                </div>
                                <div class="refresh-shot-side">
                                    <div class="refresh-side-title">Action Center</div>
                                    <div class="refresh-side-text">Top issues move directly into team tasks with owners and follow-up dates.</div>
                                    <div class="refresh-side-bar"><i style="width:72%;"></i></div>
                                    <div class="refresh-side-title">Version Comparison</div>
                                    <div class="refresh-side-text">Installation pain is down in V2, while packaging is becoming the new leading risk.</div>
                                    <div class="refresh-side-bar"><i style="width:54%;"></i></div>
                                    <div class="refresh-side-title">Follow-up Validation</div>
                                    <div class="refresh-side-text">Later reviews are ready to confirm whether the packaging update actually worked.</div>
                                    <div class="refresh-side-bar"><i style="width:61%;"></i></div>
                                </div>
                            </div>
                        </div>
                        <div class="refresh-callouts">
                            <div class="refresh-callout">
                                <strong>Top issues should not stay abstract</strong>
                                <p>Every major complaint should connect to an owner, an action, and a follow-up checkpoint instead of staying in a static report.</p>
                            </div>
                            <div class="refresh-callout">
                                <strong>The visual should feel like a real product</strong>
                                <p>The homepage uses a realistic dashboard-style composition first, then short copy to explain the value.</p>
                            </div>
                            <div class="refresh-callout">
                                <strong>Lead with today's decision</strong>
                                <p>The page explains what to do next before it explains the full feature map.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """,
        )
    )

    _render_workspace_return()
    _render_primary_actions("landing_refresh_primary")

    _render_html_block(
        pick(
            """
            <div class="refresh-shell refresh-section">
                <div class="refresh-section-head">
                    <div>
                        <strong>首页先讲价值，再讲功能。</strong>
                        <span>新版欢迎页不再把首页做成说明书，而是用更少的信息帮用户快速建立判断：上传评论后，马上能得到什么业务价值。</span>
                    </div>
                </div>
                <div class="refresh-card refresh-surface">
                    <div class="refresh-value-grid">
                        <div class="refresh-value-item">
                            <div class="refresh-index">01</div>
                            <strong>发现高风险问题</strong>
                            <p>不是先看一堆图表，而是先知道最近哪一个问题上升最快、最影响销量和口碑。</p>
                        </div>
                        <div class="refresh-value-item">
                            <div class="refresh-index">02</div>
                            <strong>把问题直接变成动作</strong>
                            <p>从评论结果页进入行动中心，把团队下一步该做什么直接定义清楚，而不是只停留在“知道了”。</p>
                        </div>
                        <div class="refresh-value-item">
                            <div class="refresh-index">03</div>
                            <strong>验证改进是否真的有效</strong>
                            <p>包装、Listing、结构或功能改完之后，继续用后续评论验证结果，形成真正的产品闭环。</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            """
            <div class="refresh-shell refresh-section">
                <div class="refresh-section-head">
                    <div>
                        <strong>Lead with value, not with a feature manual.</strong>
                        <span>The new landing page reduces noise so a first-time visitor can quickly understand what business value appears right after upload.</span>
                    </div>
                </div>
                <div class="refresh-card refresh-surface">
                    <div class="refresh-value-grid">
                        <div class="refresh-value-item">
                            <div class="refresh-index">01</div>
                            <strong>Spot high-risk issues first</strong>
                            <p>Instead of starting from charts, start from the issue that is rising fastest and has the most business impact.</p>
                        </div>
                        <div class="refresh-value-item">
                            <div class="refresh-index">02</div>
                            <strong>Turn findings into actions</strong>
                            <p>Move directly from review insights into the Action Center so the next team step becomes explicit.</p>
                        </div>
                        <div class="refresh-value-item">
                            <div class="refresh-index">03</div>
                            <strong>Prove whether changes worked</strong>
                            <p>Use later reviews to validate packaging, listing, structural, or feature changes and complete the loop.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
        )
    )

    _render_html_block(
        pick(
            """
            <div class="refresh-shell refresh-section">
                <div class="refresh-section-head">
                    <div>
                        <strong>ClueAI 不只是评论总结工具。</strong>
                        <span>真正的差异化不在于“把评论分析出来”，而在于把评论洞察、责任归因和结果验证串成一个持续运转的决策流程。</span>
                    </div>
                </div>
                <div class="refresh-card refresh-surface">
                    <div class="refresh-diff-grid">
                        <div class="refresh-diff-item">
                            <div class="refresh-index">A</div>
                            <strong>评论洞察</strong>
                            <p>系统先从海量评论中提炼核心问题、亮点、趋势和证据，帮你快速理解用户在抱怨什么、认可什么。</p>
                        </div>
                        <div class="refresh-diff-item">
                            <div class="refresh-index">B</div>
                            <strong>责任归因</strong>
                            <p>问题不会只停在报告里，而是继续连接到运营、产研、质检等角色，让“谁来处理”也一并清楚。</p>
                        </div>
                        <div class="refresh-diff-item">
                            <div class="refresh-index">C</div>
                            <strong>行动闭环与复盘</strong>
                            <p>欢迎页直接表达你最终得到的是一套工作闭环，而不是一份只看一次就结束的分析输出。</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
            """
            <div class="refresh-shell refresh-section">
                <div class="refresh-section-head">
                    <div>
                        <strong>ClueAI is more than a review-summary tool.</strong>
                        <span>The real difference is not just analyzing reviews, but connecting insight, ownership, and validation into one operating flow.</span>
                    </div>
                </div>
                <div class="refresh-card refresh-surface">
                    <div class="refresh-diff-grid">
                        <div class="refresh-diff-item">
                            <div class="refresh-index">A</div>
                            <strong>Review insight</strong>
                            <p>The system extracts key issues, strengths, trends, and evidence so you can quickly understand what customers praise or complain about.</p>
                        </div>
                        <div class="refresh-diff-item">
                            <div class="refresh-index">B</div>
                            <strong>Ownership clarity</strong>
                            <p>Findings do not stay inside a report. They connect to operations, product, and QA so ownership becomes visible too.</p>
                        </div>
                        <div class="refresh-diff-item">
                            <div class="refresh-index">C</div>
                            <strong>Action loop and validation</strong>
                            <p>The homepage should make it clear that the end result is an operating loop, not a one-time static analysis output.</p>
                        </div>
                    </div>
                </div>
            </div>
            """,
        )
    )

    _render_html_block(
        pick(
            """
            <div class="refresh-shell">
                <div class="refresh-cta">
                    <strong>上传一批评论，看看今天该先解决什么。</strong>
                    <p>你可以先试用，也可以直接注册进入完整工作台。新版欢迎页先把价值说清楚，再让用户决定是否继续深入功能。</p>
                </div>
            </div>
            """,
            """
            <div class="refresh-shell">
                <div class="refresh-cta">
                    <strong>Upload one batch of reviews and see what should be solved first.</strong>
                    <p>You can start with the trial or go straight into the full workspace. The refreshed landing page explains the value first, then lets the user choose the next step.</p>
                </div>
            </div>
            """,
        )
    )

    _render_primary_actions("landing_refresh_footer")


def _render_preview_variant_switcher(active_variant: str) -> None:
    if not st.session_state.get("force_public_preview"):
        return

    _render_html_block(
        """
        <style>
        .landing-preview-switch {
            max-width: 1180px;
            margin: 18px auto 0;
            padding: 0 24px;
        }
        </style>
        """
    )
    _render_html_block("<div class='landing-preview-switch'></div>")

    col_left, col_current, col_refresh, col_right = st.columns([2.2, 1.2, 1.2, 2.2])
    with col_current:
        if st.button(
            pick("当前欢迎页", "Current Landing"),
            key="landing_preview_switch_current",
            use_container_width=True,
            type="primary" if active_variant == "current" else "secondary",
        ):
            st.session_state["landing_preview_variant"] = "current"
            st.session_state["show_page"] = "landing"
            st.rerun()
    with col_refresh:
        if st.button(
            pick("新版欢迎页", "New Landing"),
            key="landing_preview_switch_refresh",
            use_container_width=True,
            type="primary" if active_variant == "refresh" else "secondary",
        ):
            st.session_state["landing_preview_variant"] = "refresh"
            st.session_state["show_page"] = "landing"
            st.rerun()


def _render_primary_actions(prefix: str) -> None:
    col_left, col_trial, col_register, col_login, col_right = st.columns([1.6, 1.15, 1.15, 1.15, 1.6])
    with col_trial:
        if st.button(pick("立即免费试用", "Try It Free"), type="primary", use_container_width=True, key=f"{prefix}_trial"):
            st.session_state["show_page"] = "trial"
            st.rerun()
    with col_register:
        if st.button(pick("注册账号", "Create Account"), use_container_width=True, key=f"{prefix}_register"):
            st.session_state["show_page"] = "login"
            st.session_state["login_default_tab"] = "register"
            st.rerun()
    with col_login:
        if st.button(pick("已有账号，登录", "Log In"), use_container_width=True, key=f"{prefix}_login"):
            st.session_state["show_page"] = "login"
            st.session_state["login_default_tab"] = "login"
            st.rerun()


def _render_workspace_return() -> None:
    if not st.session_state.get("is_logged_in"):
        return

    col_left, col_button = st.columns([4.2, 1.2])
    with col_button:
        if st.button(t("back_to_workspace"), key="landing_back_to_workspace", use_container_width=True):
            st.session_state.pop("force_public_preview", None)
            st.session_state["current_page"] = "dashboard"
            st.rerun()
