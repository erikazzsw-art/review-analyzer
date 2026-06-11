from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAI

from backend_api.app.deps import get_current_user
from backend_api.app.schemas.copywriter import (
    CopywriterGeneratedItemPayload,
    CopywriterGenerateRequest,
    CopywriterGenerateResponse,
    CopywriterIdealProfilePayload,
    CopywriterPlatformPayload,
    CopywriterProductPayload,
    CopywriterSessionPayload,
    CopywriterTypePayload,
)
from review_analyzer.analyzer import get_api_key
from review_analyzer.database import get_comments, get_session_by_id, get_sessions
from review_analyzer.paddle_billing import is_pro_user

router = APIRouter(prefix="/copywriter", tags=["copywriter"])

PLATFORM_DATA: dict[str, dict[str, Any]] = {
    "amazon": {
        "name_zh": "亚马逊站内广告文案",
        "name_en": "Amazon Ad Copy",
        "icon": "📦",
        "label_zh": "亚马逊站内",
        "label_en": "Amazon",
        "sub": "Amazon Ads",
        "types": [
            {"id": "sp", "name_zh": "SP商品推广标题", "name_en": "SP Product Ad Title", "limit": 150},
            {"id": "sd", "name_zh": "SD展示型广告文案", "name_en": "SD Display Ad Copy", "limit": 100},
            {"id": "sb", "name_zh": "SB品牌推广标语", "name_en": "SB Brand Slogan", "limit": 50},
        ],
        "prohibited": ["best", "#1", "guaranteed", "discount", "free", "cheap", "limited time", "buy now"],
        "guidelines_zh": "Amazon 禁止使用最高级词、未经验证的声明、紧迫感语言和价格诱导词。",
        "guidelines_en": "Avoid superlatives, unverifiable claims, urgency language, and price-led wording.",
    },
    "google": {
        "name_zh": "谷歌广告文案",
        "name_en": "Google Ad Copy",
        "icon": "🔍",
        "label_zh": "谷歌广告",
        "label_en": "Google Ads",
        "sub": "Google Ads",
        "types": [
            {"id": "title", "name_zh": "广告标题", "name_en": "Ad Headline", "limit": 30},
            {"id": "desc", "name_zh": "广告描述", "name_en": "Ad Description", "limit": 90},
            {"id": "ext", "name_zh": "附加信息", "name_en": "Extra Detail", "limit": 25},
        ],
        "prohibited": ["click here", "buy now", "free", "guaranteed", "#1", "best", "lowest price"],
        "guidelines_zh": "Google Ads 禁止误导性声明、过度大写、标题中的感叹号和点击诱导语言。",
        "guidelines_en": "Avoid misleading claims, all-caps emphasis, exclamation-heavy titles, and clickbait phrasing.",
    },
    "facebook": {
        "name_zh": "Facebook 广告文案",
        "name_en": "Facebook Ad Copy",
        "icon": "👤",
        "label_zh": "Facebook",
        "label_en": "Facebook",
        "sub": "Meta Ads",
        "types": [
            {"id": "primary", "name_zh": "主要文案", "name_en": "Primary Copy", "limit": 125},
            {"id": "headline", "name_zh": "标题", "name_en": "Headline", "limit": 40},
            {"id": "desc", "name_zh": "描述", "name_en": "Description", "limit": 30},
        ],
        "prohibited": ["you are", "your body", "weight loss", "before and after", "cure", "guaranteed results"],
        "guidelines_zh": "Meta 禁止针对个人属性的描述、身体羞辱、健康声明和情感操纵。",
        "guidelines_en": "Avoid personal-attribute claims, body shaming, health claims, and emotional manipulation.",
    },
    "instagram": {
        "name_zh": "Instagram 广告文案",
        "name_en": "Instagram Ad Copy",
        "icon": "📷",
        "label_zh": "Instagram",
        "label_en": "Instagram",
        "sub": "IG Ads",
        "types": [
            {"id": "post", "name_zh": "帖子文案", "name_en": "Post Copy", "limit": 2200},
            {"id": "story", "name_zh": "故事文案", "name_en": "Story Copy", "limit": 125},
            {"id": "reels", "name_zh": "Reels 标题", "name_en": "Reels Title", "limit": 100},
        ],
        "prohibited": ["you are", "your body", "weight loss", "before and after", "cure", "swipe up", "link in bio"],
        "guidelines_zh": "Instagram 遵循 Meta 政策，付费广告中避免使用 swipe up 和 link in bio。",
        "guidelines_en": "Follow Meta policy and avoid swipe up or link in bio in paid ads.",
    },
    "walmart": {
        "name_zh": "沃尔玛站内广告文案",
        "name_en": "Walmart Ad Copy",
        "icon": "🏬",
        "label_zh": "沃尔玛站内",
        "label_en": "Walmart",
        "sub": "Walmart Ads",
        "types": [
            {"id": "prodtitle", "name_zh": "商品标题", "name_en": "Product Title", "limit": 75},
            {"id": "proddesc", "name_zh": "商品描述", "name_en": "Product Description", "limit": 150},
            {"id": "slogan", "name_zh": "广告标语", "name_en": "Ad Slogan", "limit": 80},
        ],
        "prohibited": ["best", "#1", "guaranteed", "discount", "free", "cheap", "lowest price"],
        "guidelines_zh": "Walmart Connect 禁止最高级词、未经验证的声明和价格诱导词。",
        "guidelines_en": "Avoid superlatives, unverifiable claims, and price-led language.",
    },
}

STYLES = ["简洁专业", "幽默风趣", "情感共鸣", "数据驱动"]


@router.get("/platforms", response_model=list[CopywriterPlatformPayload])
def list_platforms(current_user: dict = Depends(get_current_user)) -> list[CopywriterPlatformPayload]:
    if not is_pro_user(int(current_user["id"])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Marketing copy is a Pro feature.")
    return [_platform_payload(pid, pdata) for pid, pdata in PLATFORM_DATA.items()]


@router.post("/generate", response_model=CopywriterGenerateResponse)
def generate_copywriter(
    payload: CopywriterGenerateRequest,
    current_user: dict = Depends(get_current_user),
) -> CopywriterGenerateResponse:
    user_id = int(current_user["id"])
    if not is_pro_user(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Marketing copy is a Pro feature.")

    platform = PLATFORM_DATA.get(payload.platform)
    if not platform:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported platform.")

    sessions = _load_sessions(user_id, payload.product_session_ids)
    if not sessions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please select at least one analysis session.")

    comments = []
    for session in sessions:
        comments.extend(get_comments(user_id, session_id=int(session["id"])))
    if not comments:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No review comments found for the selected sessions.")

    selected_session_payloads = [_session_payload(session) for session in sessions]
    review_summary, pos_samples, neg_samples = _build_review_summary(comments)

    generated_items: list[CopywriterGeneratedItemPayload] = []
    ideal_profile: CopywriterIdealProfilePayload | None = None

    if payload.generate_ad_copy:
        for ad_type in platform["types"]:
            current_style = payload.style_by_type.get(ad_type["id"], STYLES[0])
            prompt = _build_copy_prompt(
                platform,
                ad_type,
                current_style,
                payload.features_text,
                review_summary,
            )
            generated_items.append(_generate_copy_item(user_id, platform, ad_type, current_style, prompt))

    if payload.generate_ideal_desc:
        ideal_profile = _generate_ideal_profile(user_id, review_summary)

    return CopywriterGenerateResponse(
        platform=_platform_payload(payload.platform, platform),
        selected_sessions=selected_session_payloads,
        review_summary=review_summary,
        generated_items=generated_items,
        ideal_profile=ideal_profile,
        generated_at=datetime.utcnow(),
    )


@router.get("/sessions", response_model=list[CopywriterProductPayload])
def list_copywriter_sessions(current_user: dict = Depends(get_current_user)) -> list[CopywriterProductPayload]:
    user_id = int(current_user["id"])
    sessions = get_sessions(user_id)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session in sessions:
        product_id = str(session.get("product_id") or "").strip()
        if not product_id:
            continue
        grouped[product_id].append(session)

    rows = []
    for product_id, product_sessions in grouped.items():
        rows.append(
            CopywriterProductPayload(
                product_id=product_id,
                product_name=product_sessions[0].get("auto_title") or product_id,
                sessions=[_session_payload(session) for session in product_sessions],
            )
        )
    return rows


def _load_sessions(user_id: int, session_ids: list[int]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[int] = set()
    for session_id in session_ids:
        if session_id in seen:
            continue
        seen.add(session_id)
        session = get_session_by_id(user_id, session_id)
        if session:
            selected.append(session)
    selected.sort(key=lambda item: int(item["id"]), reverse=True)
    return selected


def _session_payload(session: dict[str, Any]) -> CopywriterSessionPayload:
    title = session.get("custom_title") or session.get("auto_title") or session.get("version") or "V1"
    total = int(session.get("total_reviews") or 0)
    positive = int(session.get("positive_count") or 0)
    negative = int(session.get("negative_count") or 0)
    return CopywriterSessionPayload(
        session_id=int(session["id"]),
        product_id=str(session.get("product_id") or ""),
        version=str(session.get("version") or "V1"),
        label=str(title),
        total_reviews=total,
        positive_count=positive,
        negative_count=negative,
        created_at=session["created_at"],
    )


def _build_review_summary(comments: list[dict[str, Any]]) -> tuple[str, list[str], list[str]]:
    pos_samples = [str(c.get("content") or "") for c in comments if c.get("sentiment") == "positive" and c.get("content")][:15]
    neg_samples = [str(c.get("content") or "") for c in comments if c.get("sentiment") == "negative" and c.get("content")][:15]
    review_summary = "Positive review summary:\n" + "\n".join(f"- {r[:100]}" for r in pos_samples)
    if neg_samples:
        review_summary += "\n\nNegative review summary:\n" + "\n".join(f"- {r[:100]}" for r in neg_samples)
    return review_summary, pos_samples, neg_samples


def _build_copy_prompt(platform: dict[str, Any], ad_type: dict[str, Any], style: str, features_text: str, review_summary: str) -> str:
    return f"""你是跨境电商广告文案专家。根据以下用户评论分析结果，为产品生成 {platform['name_zh']} 的 {ad_type['name_zh']}。

要求：
1. 风格：{style}
2. 字符限制：不超过 {ad_type['limit']} 个英文字符
3. 语言：英文为主，下方附中文翻译
4. 禁止使用以下违禁词：{', '.join(platform['prohibited'])}
5. 只输出一条文案，格式为 JSON：{{"en": "英文文案", "zh": "中文翻译"}}

{f"产品功能点：{features_text}" if features_text else ""}

{review_summary}"""


def _generate_copy_item(
    user_id: int,
    platform: dict[str, Any],
    ad_type: dict[str, Any],
    style: str,
    prompt: str,
) -> CopywriterGeneratedItemPayload:
    try:
        client = OpenAI(api_key=get_api_key(user_id), base_url="https://api.deepseek.com/v1", timeout=30.0)
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)
        en_text = str(result.get("en") or "")
        zh_text = str(result.get("zh") or "")
    except Exception as exc:
        en_text = f"Generation failed: {exc}"
        zh_text = ""

    return CopywriterGeneratedItemPayload(
        type_id=str(ad_type["id"]),
        type_name=str(ad_type["name_zh"]),
        limit=int(ad_type["limit"]),
        style=style,
        en=en_text,
        zh=zh_text,
        char_count=len(en_text),
        compliant=not any(word in en_text.lower() for word in platform["prohibited"]),
    )


def _generate_ideal_profile(user_id: int, review_summary: str) -> CopywriterIdealProfilePayload:
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
        client = OpenAI(api_key=get_api_key(user_id), base_url="https://api.deepseek.com/v1", timeout=30.0)
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        return CopywriterIdealProfilePayload(
            features=[str(item) for item in data.get("features") or []],
            price_range=str(data.get("price_range") or ""),
            logistics=str(data.get("logistics") or ""),
            packaging=str(data.get("packaging") or ""),
            service=str(data.get("service") or ""),
            summary=str(data.get("summary") or ""),
        )
    except Exception as exc:
        return CopywriterIdealProfilePayload(summary=f"Generation failed: {exc}")


def _platform_payload(platform_id: str, data: dict[str, Any]) -> CopywriterPlatformPayload:
    return CopywriterPlatformPayload(
        id=platform_id,
        name_zh=str(data["name_zh"]),
        name_en=str(data["name_en"]),
        icon=str(data["icon"]),
        label_zh=str(data["label_zh"]),
        label_en=str(data["label_en"]),
        sub=str(data["sub"]),
        types=[
            CopywriterTypePayload(
                id=str(item["id"]),
                name_zh=str(item["name_zh"]),
                name_en=str(item["name_en"]),
                limit=int(item["limit"]),
            )
            for item in data["types"]
        ],
        prohibited=[str(item) for item in data["prohibited"]],
        guidelines_zh=str(data["guidelines_zh"]),
        guidelines_en=str(data["guidelines_en"]),
    )
