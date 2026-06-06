"""推送设置页面 — 飞书 Webhook + 推送规则配置"""

import json

import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.database import get_setting, set_setting, get_sessions
from review_analyzer.i18n import pick
from review_analyzer.notifier import _test_webhook
from review_analyzer.page_shell import render_page_header


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


def _rule_row(label: str, desc: str, enabled_key: str, enabled_val: bool,
              threshold_key: str, threshold_val: int, color: str = "#ff682c") -> tuple:
    col_on, col_desc, col_val = st.columns([0.2, 5, 0.8])
    with col_on:
        enabled = st.checkbox(pick("启用", "Enable"), value=enabled_val, key=enabled_key, label_visibility="collapsed")
    with col_desc:
        st.markdown(f"""
        <div style="padding-top:6px;">
            <span style="font-size:14px;color:#202020;">{label}</span>
            <span style="font-size:12px;color:#828282;margin-left:8px;">{desc}</span>
        </div>
        """, unsafe_allow_html=True)
    with col_val:
        threshold = st.number_input(
            pick("阈值", "Threshold"), value=threshold_val, min_value=1, max_value=100,
            key=threshold_key, label_visibility="collapsed"
        )
    return enabled, threshold


def render_settings() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(pick("请先登录", "Please log in first."))
        return

    st.markdown("""
    <style>
    .settings-page .stNumberInput input { text-align: center; font-size: 14px; width: 64px !important; min-width: 56px !important; }
    .settings-page .stNumberInput { max-width: 72px !important; }
    .settings-page [data-testid="column"]:first-child { min-width: 0 !important; flex: 0 0 24px !important; max-width: 28px !important; padding-right: 0 !important; }
    .settings-page [data-testid="stCheckbox"] { padding-top: 6px; }
    .settings-page [data-testid="column"]:nth-child(2) { padding-left: 0 !important; }
    </style>
    <div class="settings-page"></div>
    """, unsafe_allow_html=True)

    render_page_header(
        pick("推送设置", "Notification Settings"),
        pick("配置飞书 Webhook 通知渠道和自动推送规则。", "Configure your Feishu webhook channel and automated notification rules."),
        path=pick("业务协同 / 推送设置", "Collaboration / Notification Settings"),
    )

    settings = _load_settings(user_id)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. 飞书 Webhook
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">1</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">%s</span>
        <span style="font-size:12px;color:#828282;margin-left:4px;">%s</span>
    </div>
    """ % (
        pick("飞书 Webhook", "Feishu Webhook"),
        pick("配置机器人 Webhook 地址，用于接收告警和通知推送", "Configure a bot webhook URL for alerts and notification pushes"),
    ), unsafe_allow_html=True)

    webhook_url = st.text_input(
        "Webhook URL",
        value=settings.get("webhook_url", ""),
        placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/...",
        key="settings_webhook_url",
    )

    col1, col2 = st.columns(2)
    with col1:
        webhook_secret = st.text_input(
            pick("加签密钥", "Signing Secret"),
            value=settings.get("webhook_secret", ""),
            placeholder="SEC...",
            key="settings_webhook_secret",
            type="password",
        )
    with col2:
        webhook_group = st.text_input(
            pick("群名称备注", "Group Label"),
            value=settings.get("webhook_group_name", ""),
            placeholder=pick("如：产品质量群", "e.g. Product Quality Group"),
            key="settings_webhook_group",
        )

    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        if st.button(pick("测试连接", "Test Connection"), key="test_webhook", type="primary"):
            if not webhook_url:
                st.error(pick("请先填写 Webhook URL", "Please enter the Webhook URL first."))
            else:
                with st.spinner(pick("正在测试连接...", "Testing connection...")):
                    result = _test_webhook(webhook_url, "feishu", webhook_secret)
                if result["ok"]:
                    st.success(pick("连接成功", "Connection successful"))
                else:
                    st.error(f"{pick('连接失败：', 'Connection failed: ')}{result['msg']}")
    with col_btn2:
        st.button(pick("+ 添加群", "+ Add Group"), key="add_webhook_group")

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. 全局推送规则
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">2</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">%s</span>
        <span style="font-size:12px;color:#828282;margin-left:4px;">%s</span>
    </div>
    """ % (
        pick("全局推送规则", "Global Notification Rules"),
        pick("适用于所有产品，任一条件触发即推送", "Applies to all products and pushes when any selected rule is triggered"),
    ), unsafe_allow_html=True)

    rules = settings.get("rules", {})

    # ── 问题监控 ──
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin:16px 0 10px;">
        <span style="width:6px;height:6px;border-radius:50%;background:#e74c3c;display:inline-block;"></span>
        <span style="font-size:14px;font-weight:600;color:#202020;">%s</span>
    </div>
    """ % pick("问题监控", "Issue Monitoring"), unsafe_allow_html=True)

    issue_pct_enabled, issue_pct = _rule_row(
        pick("产品问题占比达到阈值", "Issue share reaches the threshold"),
        pick("超过此 % 时触发", "Triggers when it exceeds this %"),
        "rule_issue_pct_enabled", rules.get("issue_pct_enabled", True),
        "rule_issue_pct", rules.get("issue_pct_threshold", 5),
    )

    neg_rate_enabled, neg_rate = _rule_row(
        pick("负面评价率达到阈值", "Negative review rate reaches the threshold"),
        pick("超过此 % 时触发", "Triggers when it exceeds this %"),
        "rule_neg_rate_enabled", rules.get("neg_rate_enabled", True),
        "rule_neg_rate", rules.get("neg_rate_threshold", 25),
    )

    # ── 环比监控 ──
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin:20px 0 10px;">
        <span style="width:6px;height:6px;border-radius:50%;background:#3498db;display:inline-block;"></span>
        <span style="font-size:14px;font-weight:600;color:#202020;">%s</span>
    </div>
    """ % pick("环比监控", "Trend Monitoring"), unsafe_allow_html=True)

    neg_compare_enabled, neg_compare_threshold = _rule_row(
        pick("负面率环比上升达到阈值", "Negative rate increase reaches the threshold"),
        pick("与上一周期相比上升超过此 %", "Compared with the previous period, it rises above this %"),
        "rule_neg_compare_enabled", rules.get("neg_rate_compare_enabled", True),
        "rule_neg_compare", rules.get("neg_rate_compare_threshold", 5),
    )

    col_w, col_v = st.columns(2)
    with col_w:
        window_options = pick(
            ["最近 14 天", "最近 30 天", "最近 60 天", "最近 180 天"],
            ["Last 14 Days", "Last 30 Days", "Last 60 Days", "Last 180 Days"],
        )
        neg_window = st.selectbox(pick("对比时间窗口", "Comparison Window"), window_options, index=1, key="rule_neg_window")
    with col_v:
        version_options = pick(
            ["同版本不同时间段", "不同版本相同时间段"],
            ["Same Version Across Time", "Different Versions in the Same Time Range"],
        )
        neg_version = st.selectbox(pick("版本维度", "Version Dimension"), version_options, key="rule_neg_version")

    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    issue_compare_enabled, issue_compare_threshold = _rule_row(
        pick("问题环比上升达到阈值", "Issue increase reaches the threshold"),
        pick("与上一周期相比上升超过此 %", "Compared with the previous period, it rises above this %"),
        "rule_issue_compare_enabled", rules.get("issue_compare_enabled", False),
        "rule_issue_compare", rules.get("issue_compare_threshold", 3),
    )

    # ── 亮点监控 ──
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin:20px 0 10px;">
        <span style="width:6px;height:6px;border-radius:50%;background:#2ecc71;display:inline-block;"></span>
        <span style="font-size:14px;font-weight:600;color:#202020;">%s</span>
    </div>
    """ % pick("亮点监控", "Highlight Monitoring"), unsafe_allow_html=True)

    hl_pct_enabled, hl_pct = _rule_row(
        pick("产品亮点占比达到阈值", "Highlight share reaches the threshold"),
        pick("超过此 % 时通知", "Notifies when it exceeds this %"),
        "rule_hl_pct_enabled", rules.get("highlight_pct_enabled", False),
        "rule_hl_pct", rules.get("highlight_pct_threshold", 10),
    )

    hl_compare_enabled, hl_compare_threshold = _rule_row(
        pick("亮点环比上升达到阈值", "Highlight increase reaches the threshold"),
        pick("与上一周期相比上升超过此 %", "Compared with the previous period, it rises above this %"),
        "rule_hl_compare_enabled", rules.get("highlight_compare_enabled", False),
        "rule_hl_compare", rules.get("highlight_compare_threshold", 5),
    )

    # ── 其他 ──
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin:20px 0 10px;">
        <span style="width:6px;height:6px;border-radius:50%;background:#828282;display:inline-block;"></span>
        <span style="font-size:14px;font-weight:600;color:#202020;">%s</span>
    </div>
    """ % pick("其他", "Other"), unsafe_allow_html=True)

    auto_push = st.checkbox(
        pick("新批次分析完成后自动推送摘要", "Push the summary automatically after a new batch is analyzed"),
        value=rules.get("auto_push_new_batch", False),
        key="rule_auto_push",
    )

    st.markdown("""
    <div style="margin-top:12px;font-size:12px;color:#828282;line-height:1.6;">
        %s
    </div>
    """ % pick("提示：环比对比时，若所选时间段内数据不足，系统将提示调整时间范围。", "Tip: if there is not enough data in the selected range for a comparison, the system will ask you to adjust the time window."),
    unsafe_allow_html=True)

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. 产品级自定义规则
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">3</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">%s</span>
        <span style="font-size:12px;color:#828282;margin-left:4px;">%s</span>
    </div>
    """ % (
        pick("产品级规则", "Product-Level Rules"),
        pick("为特定产品设置不同阈值，覆盖全局规则", "Set different thresholds for specific products to override the global rules"),
    ), unsafe_allow_html=True)

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
                    st.number_input(pick("问题%", "Issue %"), value=rule.get("issue_pct", 5), min_value=1, max_value=100, key=f"pr_issue_{i}")
                with cols[2]:
                    st.number_input(pick("负面%", "Negative %"), value=rule.get("neg_rate", 25), min_value=1, max_value=100, key=f"pr_neg_{i}")
                with cols[3]:
                    st.number_input(pick("亮点%", "Highlight %"), value=rule.get("hl_pct", 10), min_value=1, max_value=100, key=f"pr_hl_{i}")
                with cols[4]:
                    st.checkbox(pick("启用", "Enable"), value=rule.get("enabled", True), key=f"pr_enabled_{i}")
                with cols[5]:
                    st.button(pick("删除", "Delete"), key=f"pr_del_{i}")
    else:
        st.markdown(f'<div style="font-size:13px;color:#828282;padding:16px 0;">{pick("暂无自定义规则，点击下方按钮添加", "No custom rules yet. Click below to add one.")}</div>', unsafe_allow_html=True)

    if st.button(pick("+ 添加产品规则", "+ Add Product Rule"), key="add_product_rule"):
        if product_ids:
            product_rules.append({
                "product_id": product_ids[0],
                "name": "",
                "issue_pct": 5,
                "neg_rate": 25,
                "hl_pct": 10,
                "enabled": True,
            })

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. 推送预览
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">4</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">%s</span>
        <span style="font-size:12px;color:#828282;margin-left:4px;">%s</span>
    </div>
    """ % (
        pick("推送预览", "Notification Preview"),
        pick("飞书群消息示例", "Example Feishu group messages"),
    ), unsafe_allow_html=True)

    tab1, tab2 = st.tabs(pick(["问题告警", "亮点通知"], ["Issue Alert", "Highlight Notice"]))

    with tab1:
        st.markdown("""
        <div style="background:#fff5f5;border-radius:8px;padding:20px;font-size:13px;
                    line-height:2;border:1px solid #ffe0e0;border-left:4px solid #e74c3c;">
            <div style="font-weight:600;color:#c0392b;font-size:14px;margin-bottom:8px;">%s</div>
            <div style="color:#4d4d4d;font-weight:500;">B09XK7G4QL · %s</div>
            <div style="margin-top:10px;padding:10px 14px;background:#fff;border-radius:6px;border:1px solid #ffe0e0;">
                <div style="font-size:12px;color:#828282;margin-bottom:4px;">%s</div>
                <div style="color:#202020;">%s</div>
                <div style="color:#202020;">%s</div>
            </div>
            <div style="margin-top:10px;font-size:11px;color:#828282;">2026-05-06 14:30</div>
        </div>
        """ % (
            pick("产品问题告警", "Product Issue Alert"),
            pick("无线蓝牙耳机", "Wireless Bluetooth Earbuds"),
            pick("触发规则：问题占比 ≥ 5%", "Triggered rule: issue share ≥ 5%"),
            pick('• "包装破损" 占比 <strong style="color:#e74c3c;">8.2%</strong>（环比 ↑2.4%）', '• "Damaged packaging" share <strong style="color:#e74c3c;">8.2%</strong> (up 2.4% vs prior period)'),
            pick('• "充电异常" 占比 <strong style="color:#e74c3c;">5.3%</strong>（环比 ↑1.1%）', '• "Charging issue" share <strong style="color:#e74c3c;">5.3%</strong> (up 1.1% vs prior period)'),
        ), unsafe_allow_html=True)

    with tab2:
        st.markdown("""
        <div style="background:#f0faf4;border-radius:8px;padding:20px;font-size:13px;
                    line-height:2;border:1px solid #b8f0d8;border-left:4px solid #2ecc71;">
            <div style="font-weight:600;color:#1e8449;font-size:14px;margin-bottom:8px;">%s</div>
            <div style="color:#4d4d4d;font-weight:500;">B09XK7G4QL · %s</div>
            <div style="margin-top:10px;padding:10px 14px;background:#fff;border-radius:6px;border:1px solid #b8f0d8;">
                <div style="font-size:12px;color:#828282;margin-bottom:4px;">%s</div>
                <div style="color:#202020;">%s</div>
                <div style="color:#202020;">%s</div>
            </div>
            <div style="margin-top:10px;padding:8px 12px;background:#e8f8f0;border-radius:6px;font-size:12px;color:#1e8449;">
                %s
            </div>
            <div style="margin-top:10px;font-size:11px;color:#828282;">2026-05-06 14:30</div>
        </div>
        """ % (
            pick("产品亮点通知", "Product Highlight Notice"),
            pick("无线蓝牙耳机", "Wireless Bluetooth Earbuds"),
            pick("触发规则：亮点占比 ≥ 10%", "Triggered rule: highlight share ≥ 10%"),
            pick('• "性价比高" 占比 <strong style="color:#2ecc71;">13.3%</strong>（环比 ↑2.1%）', '• "Great value" share <strong style="color:#2ecc71;">13.3%</strong> (up 2.1% vs prior period)'),
            pick('• 代表评论："Amazing value for the price!"', '• Representative review: "Amazing value for the price!"'),
            pick('💡 建议：可在 Listing 中强化"性价比"卖点', '💡 Suggestion: strengthen the "great value" point in your listing'),
        ), unsafe_allow_html=True)

    st.markdown('<div style="height:32px;"></div>', unsafe_allow_html=True)

    # ── 保存 ─────────────────────────────────────────────────
    _, col_save = st.columns([5, 1.5])
    with col_save:
        if st.button(pick("保存设置", "Save Settings"), type="primary", use_container_width=True, key="save_settings"):
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
            st.success(pick("✓ 设置已保存", "✓ Settings saved"))
