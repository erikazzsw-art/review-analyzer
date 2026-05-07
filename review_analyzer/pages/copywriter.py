"""宣传文案页面 — 基于评论分析生成广告文案"""

import streamlit as st

from review_analyzer.auth import get_current_user_id
from review_analyzer.database import get_sessions, get_comments


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
            border_style = "border:2px solid #6C5CE7;background:#F0EEFF;" if is_active else "border:2px solid #E8EAF0;"
            if st.button(f"{pdata['icon']}\n{pdata['label']}", key=f"platform_{pid}", use_container_width=True):
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

        st.markdown("<br>", unsafe_allow_html=True)

        if gen_ad_copy:
            # 平台政策提示
            st.markdown(f"""
            <div style="padding:10px 14px;background:#F0EEFF;border-radius:8px;font-size:12px;
                        color:#636E72;line-height:1.6;border:1px solid #E0DCFF;margin-bottom:16px;">
                📋 <strong>{rules['name']}</strong>：{rules['guidelines']}
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"### 📢 {platform_info['name']}")

            # 每种广告类型一张卡片
            for ad_type in platform_info["types"]:
                st.markdown(f"""
                <div class="copy-card">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <span style="font-size:15px;font-weight:600;">{ad_type['name']}</span>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span style="font-size:12px;color:#636E72;background:#fff;padding:3px 10px;
                                         border-radius:20px;border:1px solid #E8EAF0;">≤ {ad_type['limit']} 字符</span>
                            <span class="compliance-badge pass">✓ 合规</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 风格选择器
                style_key = f"style_{platform}_{ad_type['id']}"
                if style_key not in st.session_state:
                    st.session_state[style_key] = "简洁专业"

                style_cols = st.columns(4)
                for si, style in enumerate(STYLES):
                    with style_cols[si]:
                        if st.button(style, key=f"style_btn_{platform}_{ad_type['id']}_{si}",
                                     use_container_width=True):
                            st.session_state[style_key] = style
                            st.rerun()

                # 文案内容（示例）
                st.markdown(f"""
                <div style="font-size:14px;line-height:1.8;padding:14px 16px;background:#fff;
                            border-radius:10px;border:1px solid #E8EAF0;margin:8px 0;">
                    <strong style="color:#2D3436;">Sample ad copy for {ad_type['name']} will be generated by AI...</strong>
                    <div style="border-top:1px dashed #E8EAF0;margin-top:8px;padding-top:8px;
                                font-size:12px;color:#636E72;">
                        中文翻译参考：AI 将根据评论分析结果生成对应文案
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 操作按钮
                btn_cols = st.columns([3, 1, 1])
                with btn_cols[0]:
                    st.markdown(f'<span style="font-size:12px;color:#636E72;">0 / {ad_type["limit"]} 字符</span>',
                                unsafe_allow_html=True)
                with btn_cols[1]:
                    st.button("🔄 刷新", key=f"refresh_{platform}_{ad_type['id']}")
                with btn_cols[2]:
                    st.button("📋 复制", key=f"copy_{platform}_{ad_type['id']}")

                st.markdown("<br>", unsafe_allow_html=True)

        if gen_ideal_desc:
            st.markdown("""
            <div class="settings-section" style="border-left:4px solid #00B894;">
                <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">🎯 客户理想产品描述（选品依据）</h3>
                <div style="background:#F7F8FC;border-radius:10px;padding:20px;">
                    <div style="font-size:14px;line-height:1.9;color:#2D3436;">
                        基于真实用户评论分析，客户对该品类产品的理想画像将由 AI 自动生成。<br><br>
                        分析维度包括：客户最看重的产品特性、价格预期、物流时效要求、包装品质期望等。
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 底部操作
        st.markdown("<br>", unsafe_allow_html=True)
        col_copy_all, col_export = st.columns(2)
        with col_copy_all:
            st.button("📋 复制全部文案", key="copy_all_btn")
        with col_export:
            st.button("📥 导出为文档", key="export_copy_btn")
