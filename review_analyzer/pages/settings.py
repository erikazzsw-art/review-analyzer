"""推送设置页面 — 飞书 Webhook + 推送规则配置"""

import json

import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.database import get_setting, set_setting, get_sessions
from review_analyzer.notifier import _test_webhook


def _load_settings(user_id: int) -> dict:
    raw = get_setting(user_id, "push_settings")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return {
        "webhook_url": "",
        "webhook_secret": "",
        "webhook_group_name": "",
        "rules": {
            "issue_pct_enabled": True,
            "issue_pct_threshold": 5,
            "neg_rate_enabled": True,
            "neg_rate_threshold": 25,
            "neg_rate_compare_enabled": True,
            "neg_rate_compare_threshold": 5,
            "neg_rate_compare_window": "30",
            "neg_rate_compare_version": "same_version",
            "issue_compare_enabled": False,
            "issue_compare_threshold": 3,
            "issue_compare_window": "30",
            "issue_compare_version": "same_version",
            "highlight_pct_enabled": False,
            "highlight_pct_threshold": 10,
            "highlight_compare_enabled": False,
            "highlight_compare_threshold": 5,
            "highlight_compare_window": "30",
            "highlight_compare_version": "same_version",
            "auto_push_new_batch": False,
        },
        "product_rules": [],
    }


def _section_header(title: str, subtitle: str = "") -> None:
    html = f'<div style="margin-bottom:20px;"><h3 style="font-size:18px;font-weight:700;color:#2D3436;margin:0 0 4px;">{title}</h3>'
    if subtitle:
        html += f'<p style="font-size:13px;color:#636E72;margin:0;line-height:1.5;">{subtitle}</p>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def _rule_row(label: str, enabled_key: str, enabled_val: bool,
              threshold_key: str, threshold_val: int, suffix: str = "% 时触发告警") -> tuple:
    col_on, col_desc, col_val = st.columns([0.3, 5, 1.2])
    with col_on:
        enabled = st.checkbox("启用", value=enabled_val, key=enabled_key, label_visibility="collapsed")
    with col_desc:
        st.markdown(f'<div style="font-size:14px;color:#2D3436;padding-top:6px;">{label}</div>', unsafe_allow_html=True)
    with col_val:
        threshold = st.number_input(
            "阈值", value=threshold_val, min_value=1, max_value=100,
            key=threshold_key, label_visibility="collapsed"
        )
    st.markdown(f'<div style="font-size:12px;color:#B2BEC3;margin:-8px 0 12px 32px;">{suffix}</div>', unsafe_allow_html=True)
    return enabled, threshold


def render_settings() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning("请先登录")
        return

    st.markdown("""
    <style>
    .settings-page h3 { margin-top: 0; }
    .settings-page .stNumberInput input { text-align: center; }
    .divider { border: none; border-top: 1px solid #F0F0F5; margin: 24px 0; }
    /* 缩小 checkbox 列的右侧间距 */
    [data-testid="column"]:first-child { min-width: 0 !important; flex: 0 0 32px !important; max-width: 40px !important; }
    [data-testid="stCheckbox"] { padding-top: 6px; }
    </style>
    <div class="settings-page">
        <h2 style="font-size:22px;font-weight:700;color:#2D3436;margin-bottom:4px;">推送设置</h2>
        <p style="font-size:13px;color:#636E72;margin-bottom:28px;">配置飞书 Webhook 通知和自动推送规则</p>
    </div>
    """, unsafe_allow_html=True)

    settings = _load_settings(user_id)

    # ── 飞书 Webhook ──────────────────────────────────────────
    _section_header("🔗 飞书 Webhook", "配置机器人 Webhook 地址，用于接收告警和通知推送")

    webhook_url = st.text_input(
        "Webhook URL",
        value=settings.get("webhook_url", ""),
        placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/...",
        key="settings_webhook_url",
    )

    col1, col2 = st.columns(2)
    with col1:
        webhook_secret = st.text_input(
            "加签密钥",
            value=settings.get("webhook_secret", ""),
            placeholder="SEC...",
            key="settings_webhook_secret",
            type="password",
        )
    with col2:
        webhook_group = st.text_input(
            "群名称备注",
            value=settings.get("webhook_group_name", ""),
            placeholder="如：产品质量群",
            key="settings_webhook_group",
        )

    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        if st.button("测试连接", key="test_webhook", type="primary"):
            if not webhook_url:
                st.error("请先填写 Webhook URL")
            else:
                with st.spinner("正在测试连接..."):
                    result = _test_webhook(webhook_url, "feishu", webhook_secret)
                if result["ok"]:
                    st.success("✓ 连接成功")
                else:
                    st.error(f"连接失败：{result['msg']}")
    with col_btn2:
        st.button("+ 添加群", key="add_webhook_group")

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── 全局推送规则 ──────────────────────────────────────────
    _section_header(
        "🌐 全局推送规则",
        '适用于所有产品。规则之间为"或"关系，任一条件触发即推送。'
    )

    rules = settings.get("rules", {})

    # 问题监控
    st.markdown('<div style="font-size:15px;font-weight:600;color:#6C5CE7;margin-bottom:10px;">⚠️ 问题监控</div>', unsafe_allow_html=True)

    issue_pct_enabled, issue_pct = _rule_row(
        "某个产品问题占比达到阈值",
        "rule_issue_pct_enabled", rules.get("issue_pct_enabled", True),
        "rule_issue_pct", rules.get("issue_pct_threshold", 5),
        "超过此百分比时推送告警"
    )

    neg_rate_enabled, neg_rate = _rule_row(
        "产品负面评价率达到阈值",
        "rule_neg_rate_enabled", rules.get("neg_rate_enabled", True),
        "rule_neg_rate", rules.get("neg_rate_threshold", 25),
        "超过此百分比时推送告警"
    )

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    # 环比监控
    st.markdown('<div style="font-size:15px;font-weight:600;color:#6C5CE7;margin-bottom:10px;">📊 环比监控</div>', unsafe_allow_html=True)

    neg_compare_enabled, neg_compare_threshold = _rule_row(
        "负面率环比上升达到阈值",
        "rule_neg_compare_enabled", rules.get("neg_rate_compare_enabled", True),
        "rule_neg_compare", rules.get("neg_rate_compare_threshold", 5),
        "与上一周期相比上升超过此百分比时告警"
    )

    col_w, col_v = st.columns(2)
    with col_w:
        window_options = ["最近 14 天", "最近 30 天", "最近 60 天", "最近 180 天"]
        neg_window = st.selectbox("对比时间窗口", window_options, index=1, key="rule_neg_window")
    with col_v:
        version_options = ["同版本不同时间段", "不同版本相同时间段"]
        neg_version = st.selectbox("版本维度", version_options, key="rule_neg_version")

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    issue_compare_enabled, issue_compare_threshold = _rule_row(
        "某产品问题环比上升达到阈值",
        "rule_issue_compare_enabled", rules.get("issue_compare_enabled", False),
        "rule_issue_compare", rules.get("issue_compare_threshold", 3),
        "与上一周期相比上升超过此百分比时告警"
    )

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    # 亮点监控
    st.markdown('<div style="font-size:15px;font-weight:600;color:#6C5CE7;margin-bottom:10px;">✅ 亮点监控</div>', unsafe_allow_html=True)

    hl_pct_enabled, hl_pct = _rule_row(
        "某个产品亮点占比达到阈值",
        "rule_hl_pct_enabled", rules.get("highlight_pct_enabled", False),
        "rule_hl_pct", rules.get("highlight_pct_threshold", 10),
        "超过此百分比时推送通知"
    )

    hl_compare_enabled, hl_compare_threshold = _rule_row(
        "某产品亮点环比上升达到阈值",
        "rule_hl_compare_enabled", rules.get("highlight_compare_enabled", False),
        "rule_hl_compare", rules.get("highlight_compare_threshold", 5),
        "与上一周期相比上升超过此百分比时通知"
    )

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    # 其他
    st.markdown('<div style="font-size:15px;font-weight:600;color:#6C5CE7;margin-bottom:10px;">📨 其他</div>', unsafe_allow_html=True)
    auto_push = st.checkbox(
        "新批次分析完成后自动推送摘要",
        value=rules.get("auto_push_new_batch", False),
        key="rule_auto_push",
    )

    st.markdown("""
    <div style="margin-top:16px;padding:10px 14px;background:#FAFBFE;border:1px solid #E8EAF0;
                border-radius:8px;font-size:12px;color:#636E72;line-height:1.6;">
        💡 环比对比时，若所选时间段内数据不足，系统将提示调整时间范围。
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── 产品级自定义规则 ──────────────────────────────────────
    _section_header(
        "📦 产品级规则",
        "为特定产品设置不同阈值，覆盖全局规则。"
    )

    sessions = get_sessions(user_id)
    product_ids = list(set(s["product_id"] for s in sessions))
    product_rules = settings.get("product_rules", [])

    if product_rules:
        for i, rule in enumerate(product_rules):
            with st.container():
                cols = st.columns([2, 1, 1, 1, 0.5, 0.5])
                with cols[0]:
                    st.text_input("SKU", value=rule.get("product_id", ""), key=f"pr_sku_{i}", label_visibility="collapsed")
                with cols[1]:
                    st.number_input("问题%", value=rule.get("issue_pct", 5), min_value=1, max_value=100, key=f"pr_issue_{i}")
                with cols[2]:
                    st.number_input("负面%", value=rule.get("neg_rate", 25), min_value=1, max_value=100, key=f"pr_neg_{i}")
                with cols[3]:
                    st.number_input("亮点%", value=rule.get("hl_pct", 10), min_value=1, max_value=100, key=f"pr_hl_{i}")
                with cols[4]:
                    st.checkbox("启用", value=rule.get("enabled", True), key=f"pr_enabled_{i}")
                with cols[5]:
                    st.button("🗑️", key=f"pr_del_{i}")
    else:
        st.markdown('<div style="font-size:13px;color:#B2BEC3;padding:12px 0;">暂无自定义规则，点击下方按钮添加</div>', unsafe_allow_html=True)

    if st.button("+ 添加产品规则", key="add_product_rule"):
        if product_ids:
            product_rules.append({
                "product_id": product_ids[0],
                "name": "",
                "issue_pct": 5,
                "neg_rate": 25,
                "hl_pct": 10,
                "enabled": True,
            })

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── 推送预览 ─────────────────────────────────────────────
    _section_header("📋 推送预览", "飞书群消息示例")

    tab1, tab2 = st.tabs(["⚠️ 问题告警", "✅ 亮点通知"])

    with tab1:
        st.markdown("""
        <div style="background:#FFFBFB;border-radius:10px;padding:16px 20px;font-size:13px;
                    line-height:2;border:1px solid #FFE0E0;">
            <div style="font-weight:600;color:#E74C3C;margin-bottom:4px;">⚠️ 产品问题告警</div>
            <div style="color:#636E72;">B09XK7G4QL · 无线蓝牙耳机</div>
            <div style="margin-top:8px;">📌 触发规则：问题占比 ≥ 5%</div>
            <div>📊 问题详情：</div>
            <div style="padding-left:16px;">• "包装破损" 占比 8.2%（环比 ↑2.4%）</div>
            <div style="padding-left:16px;">• "充电异常" 占比 5.3%（环比 ↑1.1%）</div>
            <div style="margin-top:8px;color:#B2BEC3;">⏰ 2026-05-06 14:30</div>
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.markdown("""
        <div style="background:#F0FFF4;border-radius:10px;padding:16px 20px;font-size:13px;
                    line-height:2;border:1px solid #B8F0D8;">
            <div style="font-weight:600;color:#00B894;margin-bottom:4px;">✅ 产品亮点通知</div>
            <div style="color:#636E72;">B09XK7G4QL · 无线蓝牙耳机</div>
            <div style="margin-top:8px;">📌 触发规则：亮点占比 ≥ 10%</div>
            <div>📊 亮点详情：</div>
            <div style="padding-left:16px;">• "性价比高" 占比 13.3%（环比 ↑2.1%）</div>
            <div style="padding-left:16px;">• 代表评论："Amazing value for the price!"</div>
            <div style="margin-top:8px;">💡 建议：可在 Listing 中强化"性价比"卖点</div>
            <div style="color:#B2BEC3;">⏰ 2026-05-06 14:30</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    # ── 保存 ─────────────────────────────────────────────────
    _, col_save = st.columns([5, 1.5])
    with col_save:
        if st.button("保存设置", type="primary", use_container_width=True, key="save_settings"):
            new_settings = {
                "webhook_url": webhook_url,
                "webhook_secret": webhook_secret,
                "webhook_group_name": webhook_group,
                "rules": {
                    "issue_pct_enabled": issue_pct_enabled,
                    "issue_pct_threshold": issue_pct,
                    "neg_rate_enabled": neg_rate_enabled,
                    "neg_rate_threshold": neg_rate,
                    "neg_rate_compare_enabled": neg_compare_enabled,
                    "neg_rate_compare_threshold": neg_compare_threshold,
                    "issue_compare_enabled": issue_compare_enabled,
                    "issue_compare_threshold": issue_compare_threshold,
                    "highlight_pct_enabled": hl_pct_enabled,
                    "highlight_pct_threshold": hl_pct,
                    "highlight_compare_enabled": hl_compare_enabled,
                    "highlight_compare_threshold": hl_compare_threshold,
                    "auto_push_new_batch": auto_push,
                },
                "product_rules": product_rules,
            }
            set_setting(user_id, "push_settings", json.dumps(new_settings, ensure_ascii=False))
            st.success("✓ 设置已保存")
