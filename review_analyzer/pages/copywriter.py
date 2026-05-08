"""宣传文案页面 — 基于评论分析生成广告文案"""

import json
import os

import streamlit as st
from openai import OpenAI

from review_analyzer.auth import get_current_user_id
from review_analyzer.database import get_sessions, get_comments
from review_analyzer.analyzer import get_api_key


PLATFORM_DATA = {
    "amazon": {
        "name": "亚马逊站内广告文案",
        "icon": "📦",
        "label": "亚马逊站内",
        "sub": "Amazon Ads",
        "types": [
            {"id": "sp", "name": "SP商品推广标题", "limit": 150},
            {"id": "sd", "name": "SD展示型广告文案", "limit": 100},
            {"id": "sb", "name": "SB品牌推广标语", "limit": 50},
        ],
    },
    "google": {
        "name": "谷歌广告文案",
        "icon": "🔍",
        "label": "谷歌广告",
        "sub": "Google Ads",
        "types": [
            {"id": "title", "name": "广告标题", "limit": 30},
            {"id": "desc", "name": "广告描述", "limit": 90},
            {"id": "ext", "name": "附加信息", "limit": 25},
        ],
    },
    "facebook": {
        "name": "Facebook 广告文案",
        "icon": "👤",
        "label": "Facebook",
        "sub": "Meta Ads",
        "types": [
            {"id": "primary", "name": "主要文案", "limit": 125},
            {"id": "headline", "name": "标题", "limit": 40},
            {"id": "desc", "name": "描述", "limit": 30},
        ],
    },
    "instagram": {
        "name": "Instagram 广告文案",
        "icon": "📷",
        "label": "Instagram",
        "sub": "IG Ads",
        "types": [
            {"id": "post", "name": "帖子文案", "limit": 2200},
            {"id": "story", "name": "故事文案", "limit": 125},
            {"id": "reels", "name": "Reels标题", "limit": 100},
        ],
    },
    "walmart": {
        "name": "沃尔玛站内广告文案",
        "icon": "🏬",
        "label": "沃尔玛站内",
        "sub": "Walmart Ads",
        "types": [
            {"id": "prodtitle", "name": "商品标题", "limit": 75},
            {"id": "proddesc", "name": "商品描述", "limit": 150},
            {"id": "slogan", "name": "广告标语", "limit": 80},
        ],
    },
}

PLATFORM_RULES = {
    "amazon": {
        "name": "Amazon Advertising Policy",
        "prohibited": ["best", "#1", "guaranteed", "discount", "free", "cheap", "limited time", "buy now"],
        "guidelines": "Amazon 禁止使用最高级词（best, #1）、未经验证的声明、紧迫感语言（hurry, limited time）、价格诱导词（discount, free, cheap）。",
    },
    "google": {
        "name": "Google Ads Policy",
        "prohibited": ["click here", "buy now", "free", "guaranteed", "#1", "best", "lowest price"],
        "guidelines": "Google Ads 禁止误导性声明、过度大写、标题中的感叹号、不可验证的最高级、点击诱导语言。标题不超过30字符，描述不超过90字符。",
    },
    "facebook": {
        "name": "Meta (Facebook) Advertising Policy",
        "prohibited": ["you are", "your body", "weight loss", "before and after", "cure", "guaranteed results"],
        "guidelines": "Meta 禁止针对个人属性的描述（you are, your body）、身体羞辱、健康声明、情感操纵、收入声明。避免对用户特征的第二人称断言。",
    },
    "instagram": {
        "name": "Instagram (Meta) Advertising Policy",
        "prohibited": ["you are", "your body", "weight loss", "before and after", "cure", "swipe up", "link in bio"],
        "guidelines": "Instagram 遵循 Meta 政策：禁止个人属性声明、身体羞辱、健康声明。付费广告中避免使用 'swipe up' 和 'link in bio'。",
    },
    "walmart": {
        "name": "Walmart Connect Advertising Policy",
        "prohibited": ["best", "#1", "guaranteed", "discount", "free", "cheap", "lowest price"],
        "guidelines": "Walmart Connect 禁止最高级词、未经验证的声明、价格语言（discount, free, cheap）、紧迫感策略。产品声明必须可验证。",
    },
}

STYLES = ["简洁专业", "幽默风趣", "情感共鸣", "数据驱动"]


def render_copywriter() -> None:
    user_id = get_current_user_id()
    if not user_id:
        st.warning("请先登录")
        return

    st.markdown("""
    <div style="margin-bottom:24px;">
        <div style="font-size:22px;font-weight:700;">生成宣传文案 & 选品依据</div>
        <div style="font-size:14px;color:#636E72;margin-top:2px;">基于真实用户评论，AI 生成产品宣传语和选品洞察</div>
    </div>
    """, unsafe_allow_html=True)

    # ① 选择产品和分析记录
    st.markdown("""
    <div class="settings-section">
        <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">① 选择产品和分析记录</h3>
    </div>
    """, unsafe_allow_html=True)

    sessions = get_sessions(user_id)
    if not sessions:
        st.info("暂无分析记录，请先上传评论并完成分析")
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
        product_options = ["请选择..."] + [f"{pid}" for pid in products.keys()]
        selected_product = st.selectbox("产品编号 *", product_options, key="copy_product")
    with col2:
        version_options = ["全部版本"]
        if selected_product != "请选择...":
            versions = set(s["version"] for s in products.get(selected_product, []))
            version_options += sorted(versions)
        selected_version = st.selectbox("版本号（选填）", version_options, key="copy_version")

    # 分析记录表格
    if selected_product != "请选择...":
        product_sessions = products.get(selected_product, [])
        if selected_version != "全部版本":
            product_sessions = [s for s in product_sessions if s["version"] == selected_version]

        st.markdown("**选择分析记录：**")
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
                st.write(dr or "—")
            with col_num:
                st.write(f"{total:,}")
            with col_rate:
                st.markdown(f'<span class="tag tag-pos">{pos_rate}</span>', unsafe_allow_html=True)

        st.session_state["copy_selected_sessions"] = selected_sessions

    st.markdown("<br>", unsafe_allow_html=True)

    # ② 选择投放平台
    st.markdown("""
    <div class="settings-section">
        <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">② 选择投放平台</h3>
    </div>
    """, unsafe_allow_html=True)

    if "copy_platform" not in st.session_state:
        st.session_state["copy_platform"] = "amazon"

    platform_cols = st.columns(5)
    for i, (pid, pdata) in enumerate(PLATFORM_DATA.items()):
        with platform_cols[i]:
            is_active = st.session_state["copy_platform"] == pid
            btn_type = "primary" if is_active else "secondary"
            if st.button(f"{pdata['icon']} {pdata['label']}", key=f"platform_{pid}",
                         use_container_width=True, type=btn_type):
                st.session_state["copy_platform"] = pid
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ③ 自定义产品功能点
    st.markdown("""
    <div class="settings-section">
        <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">③ 自定义产品功能点（选填）</h3>
        <p style="font-size:13px;color:#636E72;margin-bottom:10px;">填写产品核心卖点，系统将结合评论分析结果生成更精准的文案</p>
    </div>
    """, unsafe_allow_html=True)

    feature_points = st.text_area(
        "产品功能点",
        placeholder="例如：主动降噪、续航12小时、IPX5防水、蓝牙5.3、轻量设计仅38g...（多个功能点用逗号或换行分隔）",
        key="copy_features",
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ④ 选择生成内容
    st.markdown("""
    <div class="settings-section">
        <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">④ 选择生成内容</h3>
    </div>
    """, unsafe_allow_html=True)

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        gen_ad_copy = st.checkbox("平台广告文案", value=True, key="copy_gen_ad")
    with col_opt2:
        gen_ideal_desc = st.checkbox("客户理想产品描述", value=True, key="copy_gen_ideal")

    col_gen = st.columns([3, 1])
    with col_gen[1]:
        generate_clicked = st.button("🪄 生成文案", type="primary", use_container_width=True, key="copy_generate")

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
        review_summary = "正面评论摘要:\n" + "\n".join(f"- {r[:100]}" for r in pos_samples)
        if neg_samples:
            review_summary += "\n\n负面评论摘要:\n" + "\n".join(f"- {r[:100]}" for r in neg_samples)

        features_text = st.session_state.get("copy_features", "")

        st.markdown("<br>", unsafe_allow_html=True)

        if gen_ad_copy:
            st.markdown(f"""
            <div style="padding:10px 14px;background:#F0EEFF;border-radius:8px;font-size:12px;
                        color:#636E72;line-height:1.6;border:1px solid #E0DCFF;margin-bottom:16px;">
                📋 <strong>{rules['name']}</strong>：{rules['guidelines']}
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"**{platform_info['name']}**")

            for ad_type in platform_info["types"]:
                st.markdown(f"**{ad_type['name']}**（≤ {ad_type['limit']} 字符）")

                style_key = f"style_{platform}_{ad_type['id']}"
                if style_key not in st.session_state:
                    st.session_state[style_key] = "简洁专业"

                style_cols = st.columns(4)
                for si, style in enumerate(STYLES):
                    with style_cols[si]:
                        btn_type = "primary" if st.session_state[style_key] == style else "secondary"
                        if st.button(style, key=f"style_btn_{platform}_{ad_type['id']}_{si}",
                                     use_container_width=True, type=btn_type):
                            st.session_state[style_key] = style
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
                    prompt = f"""你是跨境电商广告文案专家。根据以下用户评论分析结果，为产品生成{platform_info['name']}的{ad_type['name']}。

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
                        st.session_state[result_key] = {"en": f"生成失败: {e}", "zh": ""}

                copy_result = st.session_state.get(result_key, {})
                en_text = copy_result.get("en", "")
                zh_text = copy_result.get("zh", "")
                char_count = len(en_text)
                is_compliant = not any(w in en_text.lower() for w in rules["prohibited"])
                badge = '<span class="compliance-badge pass">✓ 合规</span>' if is_compliant else '<span class="compliance-badge warn">⚠ 有风险</span>'

                st.markdown(f"""
                <div style="font-size:14px;line-height:1.8;padding:14px 16px;background:#fff;
                            border-radius:10px;border:1px solid #E8EAF0;margin:8px 0;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                        <span style="font-size:12px;color:#636E72;">{char_count} / {ad_type['limit']} 字符</span>
                        {badge}
                    </div>
                    <strong style="color:#2D3436;">{en_text}</strong>
                    <div style="border-top:1px dashed #E8EAF0;margin-top:8px;padding-top:8px;
                                font-size:12px;color:#636E72;">
                        中文参考：{zh_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                btn_cols = st.columns([4, 1])
                with btn_cols[1]:
                    if st.button("刷新", key=refresh_key, use_container_width=True):
                        if result_key in st.session_state:
                            del st.session_state[result_key]
                        st.rerun()

                st.markdown("")

        if gen_ideal_desc:
            st.markdown("**客户理想产品描述（选品依据）**")

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
                    st.session_state[ideal_key] = {"summary": f"生成失败: {e}"}

            ideal = st.session_state.get(ideal_key, {})
            features = ideal.get("features", [])
            summary = ideal.get("summary", "")

            features_html = " ".join(f'<span class="tag tag-topic">{f}</span>' for f in features)
            st.markdown(f"""
            <div class="settings-section" style="border-left:4px solid #00B894;">
                <div style="margin-bottom:12px;">{features_html}</div>
                <div style="font-size:14px;line-height:1.9;color:#2D3436;">
                    {summary}
                </div>
                <div style="margin-top:12px;font-size:13px;color:#636E72;">
                    价格预期：{ideal.get('price_range', '—')} ｜
                    物流要求：{ideal.get('logistics', '—')} ｜
                    包装期望：{ideal.get('packaging', '—')} ｜
                    售后要求：{ideal.get('service', '—')}
                </div>
            </div>
            """, unsafe_allow_html=True)
