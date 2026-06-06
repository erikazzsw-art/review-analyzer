"""宣传文案页面 — 基于评论分析生成广告文案"""

import json

import streamlit as st
from openai import OpenAI

from review_analyzer.auth import get_current_user_id
from review_analyzer.analyzer import get_api_key
from review_analyzer.database import get_sessions, get_comments
from review_analyzer.i18n import pick
from review_analyzer.page_shell import render_page_header


PLATFORM_DATA = {
    "amazon": {
        "name": {"zh": "亚马逊站内广告文案", "en": "Amazon Ad Copy"},
        "icon": "📦",
        "label": {"zh": "亚马逊站内", "en": "Amazon"},
        "sub": "Amazon Ads",
        "types": [
            {"id": "sp", "name": {"zh": "SP商品推广标题", "en": "SP Product Ad Title"}, "limit": 150},
            {"id": "sd", "name": {"zh": "SD展示型广告文案", "en": "SD Display Ad Copy"}, "limit": 100},
            {"id": "sb", "name": {"zh": "SB品牌推广标语", "en": "SB Brand Slogan"}, "limit": 50},
        ],
    },
    "google": {
        "name": {"zh": "谷歌广告文案", "en": "Google Ad Copy"},
        "icon": "🔍",
        "label": {"zh": "谷歌广告", "en": "Google Ads"},
        "sub": "Google Ads",
        "types": [
            {"id": "title", "name": {"zh": "广告标题", "en": "Ad Headline"}, "limit": 30},
            {"id": "desc", "name": {"zh": "广告描述", "en": "Ad Description"}, "limit": 90},
            {"id": "ext", "name": {"zh": "附加信息", "en": "Extra Detail"}, "limit": 25},
        ],
    },
    "facebook": {
        "name": {"zh": "Facebook 广告文案", "en": "Facebook Ad Copy"},
        "icon": "👤",
        "label": {"zh": "Facebook", "en": "Facebook"},
        "sub": "Meta Ads",
        "types": [
            {"id": "primary", "name": {"zh": "主要文案", "en": "Primary Copy"}, "limit": 125},
            {"id": "headline", "name": {"zh": "标题", "en": "Headline"}, "limit": 40},
            {"id": "desc", "name": {"zh": "描述", "en": "Description"}, "limit": 30},
        ],
    },
    "instagram": {
        "name": {"zh": "Instagram 广告文案", "en": "Instagram Ad Copy"},
        "icon": "📷",
        "label": {"zh": "Instagram", "en": "Instagram"},
        "sub": "IG Ads",
        "types": [
            {"id": "post", "name": {"zh": "帖子文案", "en": "Post Copy"}, "limit": 2200},
            {"id": "story", "name": {"zh": "故事文案", "en": "Story Copy"}, "limit": 125},
            {"id": "reels", "name": {"zh": "Reels标题", "en": "Reels Title"}, "limit": 100},
        ],
    },
    "walmart": {
        "name": {"zh": "沃尔玛站内广告文案", "en": "Walmart Ad Copy"},
        "icon": "🏬",
        "label": {"zh": "沃尔玛站内", "en": "Walmart"},
        "sub": "Walmart Ads",
        "types": [
            {"id": "prodtitle", "name": {"zh": "商品标题", "en": "Product Title"}, "limit": 75},
            {"id": "proddesc", "name": {"zh": "商品描述", "en": "Product Description"}, "limit": 150},
            {"id": "slogan", "name": {"zh": "广告标语", "en": "Ad Slogan"}, "limit": 80},
        ],
    },
}

PLATFORM_RULES = {
    "amazon": {
        "name": "Amazon Advertising Policy",
        "prohibited": ["best", "#1", "guaranteed", "discount", "free", "cheap", "limited time", "buy now"],
        "guidelines": {
            "zh": "Amazon 禁止使用最高级词（best, #1）、未经验证的声明、紧迫感语言（hurry, limited time）、价格诱导词（discount, free, cheap）。",
            "en": "Avoid superlatives like best or #1, unverifiable claims, urgency language, and price-led wording such as discount, free, or cheap.",
        },
    },
    "google": {
        "name": "Google Ads Policy",
        "prohibited": ["click here", "buy now", "free", "guaranteed", "#1", "best", "lowest price"],
        "guidelines": {
            "zh": "Google Ads 禁止误导性声明、过度大写、标题中的感叹号、不可验证的最高级、点击诱导语言。标题不超过30字符，描述不超过90字符。",
            "en": "Avoid misleading claims, all-caps emphasis, exclamation-heavy titles, unverifiable superlatives, and clickbait phrasing. Headlines should stay within 30 characters and descriptions within 90.",
        },
    },
    "facebook": {
        "name": "Meta (Facebook) Advertising Policy",
        "prohibited": ["you are", "your body", "weight loss", "before and after", "cure", "guaranteed results"],
        "guidelines": {
            "zh": "Meta 禁止针对个人属性的描述（you are, your body）、身体羞辱、健康声明、情感操纵、收入声明。避免对用户特征的第二人称断言。",
            "en": "Avoid personal-attribute claims, body shaming, health claims, emotional manipulation, and income claims. Do not make second-person assumptions about the audience.",
        },
    },
    "instagram": {
        "name": "Instagram (Meta) Advertising Policy",
        "prohibited": ["you are", "your body", "weight loss", "before and after", "cure", "swipe up", "link in bio"],
        "guidelines": {
            "zh": "Instagram 遵循 Meta 政策：禁止个人属性声明、身体羞辱、健康声明。付费广告中避免使用 'swipe up' 和 'link in bio'。",
            "en": "Follow Meta policy: avoid personal-attribute claims, body shaming, and health claims. In paid ads, avoid phrasing like swipe up or link in bio.",
        },
    },
    "walmart": {
        "name": "Walmart Connect Advertising Policy",
        "prohibited": ["best", "#1", "guaranteed", "discount", "free", "cheap", "lowest price"],
        "guidelines": {
            "zh": "Walmart Connect 禁止最高级词、未经验证的声明、价格语言（discount, free, cheap）、紧迫感策略。产品声明必须可验证。",
            "en": "Avoid superlatives, unverifiable claims, price-led language such as discount or free, and urgency tactics. Product claims should be supportable.",
        },
    },
}

STYLES = [
    {"zh": "简洁专业", "en": "Clear & Professional"},
    {"zh": "幽默风趣", "en": "Playful"},
    {"zh": "情感共鸣", "en": "Emotional"},
    {"zh": "数据驱动", "en": "Data-Driven"},
]


def _copy_name(value: dict[str, str]) -> str:
    return pick(value["zh"], value["en"])


def render_copywriter() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning(pick("请先登录", "Please log in first."))
        return

    render_page_header(
        pick("宣传文案", "Marketing Copy"),
        pick("基于真实用户评论，AI 生成产品宣传语和选品洞察。", "Generate ad copy and product-positioning insights from real customer reviews."),
        path=pick("业务协同 / 宣传文案", "Collaboration / Marketing Copy"),
    )

    # ① 选择产品和分析记录
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">1</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">%s</span>
    </div>
    """ % pick("选择产品和分析记录", "Choose Product and Analysis Batches"), unsafe_allow_html=True)

    sessions = get_sessions(user_id)
    if not sessions:
        st.info(pick("暂无分析记录，请先上传评论并完成分析", "No analysis records yet. Upload reviews and finish an analysis first."))
        return

    # 获取产品列表
    products = {}
    for s in sessions:
        pid = s["product_id"]
        if pid not in products:
            products[pid] = []
        products[pid].append(s)

    col1, col2 = st.columns(2)
    with col1:
        product_options = ["__placeholder__"] + [f"{pid}" for pid in products.keys()]
        selected_product = st.selectbox(
            pick("产品编号 *", "Product ID *"),
            product_options,
            key="copy_product",
            format_func=lambda value: pick("请选择...", "Please select...") if value == "__placeholder__" else value,
        )
    with col2:
        version_options = ["__all__"]
        if selected_product != "__placeholder__":
            versions = set(s["version"] for s in products.get(selected_product, []))
            version_options += sorted(versions)
        selected_version = st.selectbox(
            pick("版本号（选填）", "Version (Optional)"),
            version_options,
            key="copy_version",
            format_func=lambda value: pick("全部版本", "All Versions") if value == "__all__" else value,
        )

    # 分析记录表格
    if selected_product != "__placeholder__":
        product_sessions = products.get(selected_product, [])
        if selected_version != "__all__":
            product_sessions = [s for s in product_sessions if s["version"] == selected_version]

        st.markdown(f"**{pick('选择分析记录：', 'Choose Analysis Batches:')}**")
        selected_sessions = []
        for s in product_sessions:
            total = s.get("total_reviews", 0)
            pos_rate = f"{s.get('positive_count', 0) / total * 100:.1f}%" if total > 0 else "—"
            col_chk, col_ver, col_date, col_num, col_rate = st.columns([0.5, 1, 2, 1, 1])
            with col_chk:
                checked = st.checkbox("", key=f"copy_sess_{s['id']}", value=True, label_visibility="collapsed")
                if checked:
                    selected_sessions.append(s["id"])
            with col_ver:
                st.write(s["version"])
            with col_date:
                dr = ""
                if s.get("date_range_start") and s.get("date_range_end"):
                    dr = f"{s['date_range_start']} ~ {s['date_range_end']}"
                st.write(dr or pick("—", "—"))
            with col_num:
                st.write(f"{total:,}")
            with col_rate:
                st.markdown(f'<span class="tag tag-pos">{pos_rate}</span>', unsafe_allow_html=True)

        st.session_state["copy_selected_sessions"] = selected_sessions

    st.markdown("<br>", unsafe_allow_html=True)

    # ② 选择投放平台
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">2</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">%s</span>
    </div>
    """ % pick("选择投放平台", "Choose Destination Platform"), unsafe_allow_html=True)

    if "copy_platform" not in st.session_state:
        st.session_state["copy_platform"] = "amazon"

    platform_cols = st.columns(5)
    for i, (pid, pdata) in enumerate(PLATFORM_DATA.items()):
        with platform_cols[i]:
            is_active = st.session_state["copy_platform"] == pid
            btn_type = "primary" if is_active else "secondary"
            if st.button(f"{pdata['icon']} {_copy_name(pdata['label'])}", key=f"platform_{pid}",
                         use_container_width=True, type=btn_type):
                st.session_state["copy_platform"] = pid
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ③ 自定义产品功能点
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">3</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">%s</span>
    </div>
    <p style="font-size:13px;color:#4d4d4d;margin-bottom:10px;">%s</p>
    """ % (
        pick("自定义产品功能点（选填）", "Custom Product Features (Optional)"),
        pick("填写产品核心卖点，系统将结合评论分析结果生成更精准的文案", "Add core selling points so the system can generate more precise copy from your review insights."),
    ), unsafe_allow_html=True)

    feature_points = st.text_area(
        pick("产品功能点", "Product Features"),
        placeholder=pick(
            "例如：主动降噪、续航12小时、IPX5防水、蓝牙5.3、轻量设计仅38g...（多个功能点用逗号或换行分隔）",
            "e.g. active noise cancellation, 12-hour battery life, IPX5 water resistance, Bluetooth 5.3, lightweight 38g... (separate with commas or line breaks)",
        ),
        key="copy_features",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ④ 选择生成内容
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #ff682c;">
        <span style="background:#ff682c;color:#fff;width:24px;height:24px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;">4</span>
        <span style="font-size:16px;font-weight:600;color:#202020;">%s</span>
    </div>
    """ % pick("选择生成内容", "Choose Output Types"), unsafe_allow_html=True)

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        gen_ad_copy = st.checkbox(pick("平台广告文案", "Platform Ad Copy"), value=True, key="copy_gen_ad")
    with col_opt2:
        gen_ideal_desc = st.checkbox(pick("客户理想产品描述", "Ideal Product Profile"), value=True, key="copy_gen_ideal")

    col_gen = st.columns([3, 1])
    with col_gen[1]:
        generate_clicked = st.button(pick("🪄 生成文案", "🪄 Generate Copy"), type="primary", use_container_width=True, key="copy_generate")

    # ⑤ 生成结果
    if generate_clicked or st.session_state.get("copy_generated"):
        st.session_state["copy_generated"] = True
        platform = st.session_state.get("copy_platform", "amazon")
        platform_info = PLATFORM_DATA[platform]
        rules = PLATFORM_RULES[platform]

        # 收集评论数据用于 AI 生成
        selected_sessions = st.session_state.get("copy_selected_sessions", [])
        all_comments = []
        for sid in selected_sessions:
            all_comments.extend(get_comments(user_id, session_id=sid))

        # 取 TOP 评论摘要（正面+负面各取前15条）
        pos_samples = [c["content"] for c in all_comments if c.get("sentiment") == "positive" and c.get("content")][:15]
        neg_samples = [c["content"] for c in all_comments if c.get("sentiment") == "negative" and c.get("content")][:15]
        review_summary = "Positive review summary:\n" + "\n".join(f"- {r[:100]}" for r in pos_samples)
        if neg_samples:
            review_summary += "\n\nNegative review summary:\n" + "\n".join(f"- {r[:100]}" for r in neg_samples)

        features_text = st.session_state.get("copy_features", "")

        st.markdown("<br>", unsafe_allow_html=True)

        if gen_ad_copy:
            st.markdown(f"""
            <div style="padding:12px 16px;background:#fff0eb;border-radius:8px;font-size:12px;
                        color:#4d4d4d;line-height:1.6;border:1px solid #ffd6c4;margin-bottom:16px;">
                <strong style="color:#ff682c;">{rules['name']}</strong>: {pick(rules['guidelines']['zh'], rules['guidelines']['en'])}
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"**{_copy_name(platform_info['name'])}**")

            for ad_type in platform_info["types"]:
                st.markdown(f"**{_copy_name(ad_type['name'])}** ({pick('≤', '<=')} {ad_type['limit']} {pick('字符', 'chars')})")

                style_key = f"style_{platform}_{ad_type['id']}"
                if style_key not in st.session_state:
                    st.session_state[style_key] = STYLES[0]["zh"]

                style_cols = st.columns(4)
                for si, style in enumerate(STYLES):
                    with style_cols[si]:
                        btn_type = "primary" if st.session_state[style_key] == style["zh"] else "secondary"
                        if st.button(_copy_name(style), key=f"style_btn_{platform}_{ad_type['id']}_{si}",
                                     use_container_width=True, type=btn_type):
                            st.session_state[style_key] = style["zh"]
                            if f"copy_result_{platform}_{ad_type['id']}" in st.session_state:
                                del st.session_state[f"copy_result_{platform}_{ad_type['id']}"]
                            st.rerun()

                # AI 生成文案
                result_key = f"copy_result_{platform}_{ad_type['id']}"
                refresh_key = f"refresh_{platform}_{ad_type['id']}"

                need_generate = result_key not in st.session_state
                if st.session_state.get(f"_refresh_{refresh_key}"):
                    need_generate = True
                    st.session_state[f"_refresh_{refresh_key}"] = False

                if need_generate and all_comments:
                    current_style = st.session_state[style_key]
                    prompt = f"""你是跨境电商广告文案专家。根据以下用户评论分析结果，为产品生成{platform_info['name']['zh']}的{ad_type['name']['zh']}。

要求：
1. 风格：{current_style}
2. 字符限制：不超过 {ad_type['limit']} 个英文字符
3. 语言：英文为主，下方附中文翻译
4. 禁止使用以下违禁词：{', '.join(rules['prohibited'])}
5. 只输出一条文案，格式为 JSON：{{"en": "英文文案", "zh": "中文翻译"}}

{f'产品功能点：{features_text}' if features_text else ''}

{review_summary}"""

                    try:
                        api_key = get_api_key(user_id)
                        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1", timeout=30.0)
                        resp = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.7,
                            max_tokens=300,
                            response_format={"type": "json_object"},
                        )
                        result = json.loads(resp.choices[0].message.content)
                        st.session_state[result_key] = result
                    except Exception as e:
                        st.session_state[result_key] = {"en": f"Generation failed: {e}", "zh": ""}

                copy_result = st.session_state.get(result_key, {})
                en_text = copy_result.get("en", "")
                zh_text = copy_result.get("zh", "")
                char_count = len(en_text)
                is_compliant = not any(w in en_text.lower() for w in rules["prohibited"])
                badge = (
                    f'<span class="compliance-badge pass">{pick("✓ 合规", "✓ Compliant")}</span>'
                    if is_compliant
                    else f'<span class="compliance-badge warn">{pick("⚠ 有风险", "⚠ Risk")}</span>'
                )

                st.markdown(f"""
                <div style="font-size:14px;line-height:1.8;padding:14px 16px;background:#f9f9f9;
                            border-radius:8px;border:1px solid #e8e8e8;margin:8px 0;border-left:3px solid #ff682c;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                        <span style="font-size:12px;color:#828282;">{char_count} / {ad_type['limit']} {pick('字符', 'chars')}</span>
                        {badge}
                    </div>
                    <strong style="color:#202020;">{en_text}</strong>
                    <div style="border-top:1px dashed #e8e8e8;margin-top:8px;padding-top:8px;
                                font-size:12px;color:#4d4d4d;">
                        {pick('中文参考：', 'Chinese Reference: ')}{zh_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                btn_cols = st.columns([4, 1])
                with btn_cols[1]:
                    if st.button(pick("刷新", "Refresh"), key=refresh_key, use_container_width=True):
                        if result_key in st.session_state:
                            del st.session_state[result_key]
                        st.rerun()

                st.markdown("")

        if gen_ideal_desc:
            st.markdown(f"**{pick('客户理想产品描述（选品依据）', 'Ideal Product Profile (Sourcing Reference)')}**")

            ideal_key = "copy_ideal_desc"
            if ideal_key not in st.session_state and all_comments:
                prompt = f"""你是跨境电商选品分析师。根据以下用户评论，分析客户对该品类产品的理想画像。

输出维度：
1. 客户最看重的产品特性（前5项）
2. 价格预期范围
3. 物流时效要求
4. 包装品质期望
5. 售后服务要求

输出格式为 JSON：{{"features": ["特性1", ...], "price_range": "...", "logistics": "...", "packaging": "...", "service": "...", "summary": "一段完整的选品建议"}}

{review_summary}"""
                try:
                    api_key = get_api_key(user_id)
                    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1", timeout=30.0)
                    resp = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=600,
                        response_format={"type": "json_object"},
                    )
                    st.session_state[ideal_key] = json.loads(resp.choices[0].message.content)
                except Exception as e:
                    st.session_state[ideal_key] = {"summary": f"Generation failed: {e}"}

            ideal = st.session_state.get(ideal_key, {})
            features = ideal.get("features", [])
            summary = ideal.get("summary", "")

            features_html = " ".join(f'<span style="display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:500;margin:2px;background:#fff0eb;color:#ff682c;">{f}</span>' for f in features)
            st.markdown(f"""
            <div style="background:#f9f9f9;border-radius:8px;padding:24px;border:1px solid #e8e8e8;border-left:4px solid #2ecc71;margin-top:12px;">
                <div style="margin-bottom:12px;">{features_html}</div>
                <div style="font-size:14px;line-height:1.9;color:#202020;">
                    {summary}
                </div>
                <div style="margin-top:14px;padding-top:14px;border-top:1px solid #e8e8e8;font-size:13px;color:#4d4d4d;display:flex;gap:16px;flex-wrap:wrap;">
                    <span>💰 {pick('价格预期', 'Price Expectation')}: <strong>{ideal.get('price_range', '—')}</strong></span>
                    <span>🚚 {pick('物流要求', 'Shipping Expectation')}: <strong>{ideal.get('logistics', '—')}</strong></span>
                    <span>📦 {pick('包装期望', 'Packaging Expectation')}: <strong>{ideal.get('packaging', '—')}</strong></span>
                    <span>🛎️ {pick('售后要求', 'After-Sales Expectation')}: <strong>{ideal.get('service', '—')}</strong></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
