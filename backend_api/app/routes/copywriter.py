from __future__ import annotations

import json
import re
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
    CopywriterStylePayload,
    CopywriterTypePayload,
)
from backend_api.app.services.ideal_profile_cache import get_or_generate_ideal_profile
from review_analyzer.analyzer import get_api_key
from review_analyzer.database import get_comments
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
            {"id": "sb_headline", "name_zh": "SB品牌推广标题", "name_en": "SB Headline", "limit": 50},
            {"id": "sd_headline", "name_zh": "SD展示型广告标题", "name_en": "SD Headline", "limit": 50},
            {"id": "sd_body", "name_zh": "SD展示型广告副文案", "name_en": "SD Body Copy", "limit": 100},
        ],
        "prohibited": [
            "best", "#1", "top", "greatest",
            "guaranteed", "100% safe", "cure",
            "discount", "free", "cheap", "lowest price", "cheapest",
            "limited time", "today only", "last chance", "act now", "don't miss out",
            "buy now",
            "$ off", "% off", "save $",
        ],
        "guidelines_zh": "Amazon 禁止最高级词、未经验证的声明、紧迫语和价格诱导词；CTA 用 Shop now / Learn more。",
        "guidelines_en": "Avoid superlatives, unverifiable claims, urgency language and price-led wording; use Shop now / Learn more for CTAs.",
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
        "prohibited": ["click here", "buy now", "free", "guaranteed", "#1", "best", "lowest price", "you won't believe", "risk-free"],
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
        "prohibited": ["you are", "your body", "your weight", "weight loss", "before and after", "cure", "guaranteed results", "100%", "risk-free"],
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
    "tiktok": {
        "name_zh": "TikTok 广告文案",
        "name_en": "TikTok Ad Copy",
        "icon": "🎵",
        "label_zh": "TikTok",
        "label_en": "TikTok",
        "sub": "TikTok Ads",
        "types": [
            {"id": "infeed_caption", "name_zh": "In-Feed 文案", "name_en": "In-Feed Caption", "limit": 100},
            {"id": "spark_headline", "name_zh": "Spark Ad 标题", "name_en": "Spark Headline", "limit": 40},
            {"id": "brand_name", "name_zh": "品牌名", "name_en": "Brand Name", "limit": 40},
        ],
        "prohibited": ["link in bio", "click link in bio", "limited time", "today only", "100% guaranteed", "cure"],
        "guidelines_zh": "TikTok 付费广告禁止 link in bio 类引导，避免紧迫语和健康类索赔。",
        "guidelines_en": "TikTok paid ads disallow link-in-bio prompts; avoid urgency and health claims.",
    },
    "walmart": {
        "name_zh": "沃尔玛站内广告文案",
        "name_en": "Walmart Ad Copy",
        "icon": "🏬",
        "label_zh": "沃尔玛站内",
        "label_en": "Walmart",
        "sub": "Walmart Ads",
        "types": [
            {"id": "prodtitle", "name_zh": "商品标题", "name_en": "Product Title", "limit": 75, "internal_estimate": True},
            {"id": "proddesc", "name_zh": "商品描述", "name_en": "Product Description", "limit": 150, "internal_estimate": True},
            {"id": "slogan", "name_zh": "广告标语", "name_en": "Ad Slogan", "limit": 80, "internal_estimate": True},
        ],
        "prohibited": ["best", "#1", "guaranteed", "discount", "free", "cheap", "lowest price", "limited time", "act now"],
        "guidelines_zh": "Walmart Connect 禁止最高级词、未经验证的声明和价格诱导词；字符位为内部保守估计，发布前请二次核对。",
        "guidelines_en": "Avoid superlatives, unverifiable claims, and price-led language; character limits are internal estimates—verify before launch.",
    },
}

STYLES = ["简洁专业", "幽默风趣", "情感共鸣", "数据驱动", "紧迫促单"]

# 风格 × 平台兼容性矩阵，依据 docs/copywriter-platform-rules.md。
# 值为该风格"禁止使用"的平台 id 列表；前端 chip 灰显、服务端校验拒绝。
STYLE_INCOMPATIBLE: dict[str, list[str]] = {
    "简洁专业": [],
    "幽默风趣": [],
    "情感共鸣": [],
    "数据驱动": [],
    "紧迫促单": ["amazon", "walmart", "google"],
}


@router.get("/platforms", response_model=list[CopywriterPlatformPayload])
def list_platforms(current_user: dict = Depends(get_current_user)) -> list[CopywriterPlatformPayload]:
    if not is_pro_user(int(current_user["id"])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Marketing copy is a Pro feature.")
    return [_platform_payload(pid, pdata) for pid, pdata in PLATFORM_DATA.items()]


@router.get("/styles", response_model=list[CopywriterStylePayload])
def list_styles(current_user: dict = Depends(get_current_user)) -> list[CopywriterStylePayload]:
    if not is_pro_user(int(current_user["id"])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Marketing copy is a Pro feature.")
    return [
        CopywriterStylePayload(name=name, incompatible_on=STYLE_INCOMPATIBLE.get(name, []))
        for name in STYLES
    ]


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

    if payload.style not in STYLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported style.")
    if payload.platform in STYLE_INCOMPATIBLE.get(payload.style, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Style '{payload.style}' is not allowed on platform '{payload.platform}'.",
        )

    product_id = payload.product_id.strip()
    if not product_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="product_id is required.")

    version = (payload.version or "").strip() or None
    start_iso = (payload.start or "").strip() or None
    end_iso = (payload.end or "").strip() or None
    if payload.range == "custom" and not (start_iso and end_iso):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="custom range requires start and end (YYYY-MM-DD).",
        )

    comments = get_comments(
        user_id,
        product_id=product_id,
        version=version,
        date_start=start_iso,
        date_end=end_iso,
    )
    if not comments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No review comments found for the selected product/version/range.",
        )

    review_summary, _, _ = _build_review_summary(comments)

    generated_items: list[CopywriterGeneratedItemPayload] = []
    if payload.generate_ad_copy:
        target_types = platform["types"]
        if payload.ad_type_id:
            target_types = [t for t in platform["types"] if t["id"] == payload.ad_type_id]
            if not target_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported ad_type_id '{payload.ad_type_id}' for platform '{payload.platform}'.",
                )
        n_variants = max(1, min(int(payload.n_variants or 1), 5))
        for ad_type in target_types:
            for _ in range(n_variants):
                prompt = _build_copy_prompt(
                    platform,
                    ad_type,
                    payload.style,
                    payload.features_text,
                    review_summary,
                )
                item = _generate_validated_item(user_id, platform, ad_type, payload.style, prompt)
                generated_items.append(item)

    ideal_profile: CopywriterIdealProfilePayload | None = None
    if payload.generate_ideal_desc:
        ideal_profile = _resolve_ideal_profile(
            user_id=user_id,
            product_id=product_id,
            version=version,
            comments=comments,
            review_summary=review_summary,
            force=payload.force_regen_profile,
        )

    return CopywriterGenerateResponse(
        platform=_platform_payload(payload.platform, platform),
        review_summary=review_summary,
        review_count=len(comments),
        generated_items=generated_items,
        ideal_profile=ideal_profile,
        generated_at=datetime.utcnow(),
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

    notes = _validate_copy(en_text, platform, ad_type)
    return CopywriterGeneratedItemPayload(
        type_id=str(ad_type["id"]),
        type_name=str(ad_type["name_zh"]),
        limit=int(ad_type["limit"]),
        style=style,
        en=en_text,
        zh=zh_text,
        char_count=len(en_text),
        compliant=not notes,
        compliance_notes=notes,
    )


def _generate_validated_item(
    user_id: int,
    platform: dict[str, Any],
    ad_type: dict[str, Any],
    style: str,
    prompt: str,
) -> CopywriterGeneratedItemPayload:
    """生成一条候选；若不合规自动重生一次。两次都失败则返回最后一次结果并保留 notes。"""
    item = _generate_copy_item(user_id, platform, ad_type, style, prompt)
    if item.compliant:
        return item
    retry_prompt = prompt + (
        f"\n\n上一稿不合规（{'; '.join(item.compliance_notes)}），请严格遵守字符限制与禁用词清单，重写一条。"
    )
    return _generate_copy_item(user_id, platform, ad_type, style, retry_prompt)


_ALLCAPS_RUN_RE = re.compile(r"(?:\b[A-Z]{2,}\b\s+){2,}\b[A-Z]{2,}\b")


def _validate_copy(text: str, platform: dict[str, Any], ad_type: dict[str, Any]) -> list[str]:
    """返回违规说明列表；空列表表示合规。"""
    notes: list[str] = []
    if not text or text.startswith("Generation failed"):
        notes.append("生成失败")
        return notes
    limit = int(ad_type["limit"])
    if len(text) > limit:
        notes.append(f"超字符限制 {len(text)}/{limit}")
    lower = text.lower()
    for word in platform.get("prohibited", []):
        if word and word.lower() in lower:
            notes.append(f"含禁用词 '{word}'")
    if text.count("!") >= 2:
        notes.append("感叹号过多")
    if _ALLCAPS_RUN_RE.search(text):
        notes.append("出现 ALL-CAPS 连续段")
    return notes


def _generate_ideal_profile(user_id: int, review_summary: str) -> dict[str, Any]:
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
        return json.loads(resp.choices[0].message.content) or {}
    except Exception as exc:
        return {"summary": f"Generation failed: {exc}"}


def _resolve_ideal_profile(
    *,
    user_id: int,
    product_id: str,
    version: str | None,
    comments: list[dict[str, Any]],
    review_summary: str,
    force: bool,
) -> CopywriterIdealProfilePayload:
    payload, cached = get_or_generate_ideal_profile(
        user_id=user_id,
        product_id=product_id,
        version=version,
        comments=comments,
        generate_fn=lambda: _generate_ideal_profile(user_id, review_summary),
        force=force,
    )
    return CopywriterIdealProfilePayload(
        features=[str(item) for item in payload.get("features") or []],
        price_range=str(payload.get("price_range") or ""),
        logistics=str(payload.get("logistics") or ""),
        packaging=str(payload.get("packaging") or ""),
        service=str(payload.get("service") or ""),
        summary=str(payload.get("summary") or ""),
        cached=cached,
        generated_at=payload.get("generated_at"),
        comment_count_at_generation=int(payload.get("comment_count_at_generation") or 0),
    )


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
                internal_estimate=bool(item.get("internal_estimate", False)),
            )
            for item in data["types"]
        ],
        prohibited=[str(item) for item in data["prohibited"]],
        guidelines_zh=str(data["guidelines_zh"]),
        guidelines_en=str(data["guidelines_en"]),
    )
