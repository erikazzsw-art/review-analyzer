"""AI 分析核心 — 跨境电商评论分析"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor

from openai import AuthenticationError

from .config import CATEGORY_TAGS, DEFAULT_CATEGORY, TAG_NORMALIZE_MAP

# 反向查找表：变体 → 标准词（在模块加载时构建一次）
_TAG_LOOKUP: dict[str, str] = {
    variant.lower(): standard
    for standard, variants in TAG_NORMALIZE_MAP.items()
    for variant in variants
}

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位拥有 6 年跨境电商运营经验的评论分析专家，熟悉欧美消费者表达习惯。
对用户评论进行深度分析，输出严格符合 JSON Schema 的结果。

━━ 情感判断规则 ━━
- 有评分时：评分 ≤3 → sentiment=negative；评分 ≥4 → sentiment=positive（评分优先级高于内容）
- 无评分时：根据评论内容判断
- 评分与内容矛盾时（如2星但内容正面）：sentiment 按评分判断，但 highlight_tags 和 issue_tags 均按内容实际提取，不强制置空
- 讽刺/反语（如 "Great, broke on day one"）→ 识别为 negative
- 混合情感 → 以更强烈的一方为主情感，两类标签均填写

━━ 标签提取规则 ━━
- 每条评论提取 1-3 个 issue_tags（差评/负面内容）+ 1-3 个 highlight_tags（好评/正面内容），可同时填写
- 相似问题统一标签："包装破损""盒子压扁""运输损坏" → 统一输出"包装破损"
- 同一条评论中多个同义表述合并后只计一个标签（不重复）
- 标签格式：2-5字名词短语，优先从预设标签库选择
- 无对应内容时输出空数组 []

━━ 分类规则（针对实体商品）━━
- product_quality（产品质量）：材质差、做工粗糙、尺寸偏差、颜色差异、功能失效、不耐用、异味
- packaging_logistics（包装物流）：包装破损、物流慢、配送问题
- user_experience（使用体验）：安装困难、操作复杂、设计不合理、使用不方便
- customer_service（客服售后）：客服态度差、回复慢、退换货麻烦
- value_for_money（性价比）：价格偏高、不值这个价
- feature_request（功能需求）：缺少某功能、希望改进（有明确改进诉求时使用）
- positive_feedback（正面反馈）：质量好、物流快、服务好、性价比高（好评时使用）
- simple_praise（单纯好评）：只有评分无实质内容，或只说"不错""可以"
- invalid_garbage（无效乱码）：乱码或无意义内容
- mixed（混合评价）：同时包含明确亮点和明确问题的评论
- other（其他）：无法归类

category 选择规则：有负面内容时优先选负面分类；亮点和问题都有时选 "mixed"；纯好评选 "positive_feedback" 或 "simple_praise"

━━ 优先级判定 ━━
- 高：严重质量问题、安全隐患、共性问题
- 中：影响使用但不致命的问题
- 低：个别主观偏好、轻微瑕疵
- 无：好评或无效内容

━━ 输出格式（严格 JSON，不输出任何其他内容）━━
{
  "sentiment": "positive | negative | neutral | unrecognizable",
  "content_sentiment": "positive | negative | neutral | unrecognizable",
  "category": "product_quality | packaging_logistics | user_experience | customer_service | value_for_money | feature_request | positive_feedback | simple_praise | invalid_garbage | mixed | other",
  "priority": "高 | 中 | 低 | 无",
  "reason": "一句话理由（≤20字）",
  "improvement": "可落地的改进建议（无问题时为空字符串）",
  "issue_tags": ["标签1", "标签2"],
  "highlight_tags": ["标签1", "标签2"]
}

字段说明：
- sentiment：最终情感，有评分时由评分决定
- content_sentiment：纯基于评论文字内容的情感判断（无评论内容时与 sentiment 相同）
- issue_tags：负面问题标签数组，无问题时为 []
- highlight_tags：正面亮点标签数组，无亮点时为 []"""

# JSON 输出强化指令（追加到 SYSTEM_PROMPT 末尾，确保所有模型输出纯 JSON）
SYSTEM_PROMPT += "\n\nRespond with raw JSON only. No markdown fences, no explanation outside the JSON object."

VALID_SENTIMENTS = {"positive", "negative", "neutral", "unrecognizable"}
VALID_CATEGORIES = {
    "product_quality", "packaging_logistics", "user_experience", "customer_service", "value_for_money",
    "feature_request", "positive_feedback", "simple_praise", "invalid_garbage", "mixed", "other",
}
VALID_PRIORITIES = {"高", "中", "低", "无"}

# 每次修改 SYSTEM_PROMPT 时递增此版本号，用于追踪历史分析数据的口径一致性
PROMPT_VERSION = "v2.2"


def _normalize_tag(raw: str) -> str:
    """把 AI 输出的 tag 映射到标准词，找不到则原样返回。"""
    return _TAG_LOOKUP.get(raw.strip().lower(), raw.strip())


def _normalize_tag_field(raw: str) -> str:
    """处理逗号分隔的多个 tag，每个都归一化。"""
    if not raw:
        return ""
    return ",".join(
        _normalize_tag(t) for t in raw.split(",") if t.strip()
    )


def classify_sentiment_by_rating(rating: int | None) -> str | None:
    """根据评分判断情感（有评分时）"""
    if rating is None:
        return None
    if rating <= 3:
        return "negative"
    return "positive"


def filter_neutral_unrecognizable(
    comments: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    分离好评池、差评池、不参与统计的评论。
    返回: (positive_pool, negative_pool, excluded_pool)

    判断逻辑：
    - 有评分字段：差评池 = 评分 ≤ 3，好评池 = 评分 4-5
    - 无评分字段：依据 AI 情感判断
    - neutral / unrecognizable → excluded
    """
    positive_pool: list[dict] = []
    negative_pool: list[dict] = []
    excluded_pool: list[dict] = []

    for comment in comments:
        rating = comment.get("rating")
        sentiment = comment.get("sentiment", "")

        if rating is not None:
            try:
                rating_val = int(rating)
            except (ValueError, TypeError):
                rating_val = None
            if rating_val is not None:
                if rating_val <= 3:
                    negative_pool.append(comment)
                elif rating_val >= 4:
                    positive_pool.append(comment)
                else:
                    excluded_pool.append(comment)
                continue

        if sentiment == "negative":
            negative_pool.append(comment)
        elif sentiment == "positive":
            positive_pool.append(comment)
        else:
            excluded_pool.append(comment)

    return positive_pool, negative_pool, excluded_pool


def build_prompt(
    comment: str,
    category: str,
    rating: int | None = None,
) -> str:
    """
    构建用户 Prompt（动态注入当前类目的预设标签库）。
    包含：类目标签库 + 评分信息 + 评论内容
    """
    tags = CATEGORY_TAGS.get(category, CATEGORY_TAGS.get(DEFAULT_CATEGORY))

    negative_tags = "、".join(tags["negative"])
    positive_tags = "、".join(tags["positive"])

    parts = [
        f"## 当前产品类目：{category}",
        "",
        f"### 预设差评标签库：{negative_tags}",
        f"### 预设好评标签库：{positive_tags}",
        "",
    ]

    if rating is not None:
        parts.append(f"### 用户评分：{rating} 星")
        parts.append("")

    parts.append("### 待分析评论：")
    parts.append(comment)
    parts.append("")
    parts.append("请严格按照 JSON 格式输出分析结果，不要输出任何其他内容。")

    return "\n".join(parts)


def _call_llm(system_prompt: str, user_prompt: str, locale: str = "en") -> dict:
    """通过 LLM Router 调用分析，带 markdown fence 抢救逻辑。

    locale="en" 走 GPT-4o-mini 优先链，"zh" 走 DeepSeek 优先链。
    GPT-4o-mini 偶尔在 JSON 外加 markdown fence，用正则兜底提取。
    """
    from backend_api.app.services.llm_router import router_completion

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    resp, model_name = router_completion(
        messages=messages,
        temperature=0.1,
        max_tokens=600,
        locale=locale,
    )

    content = resp.choices[0].message.content.strip()

    # 尝试直接解析 JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 抢救：GPT-4o-mini 偶尔加 markdown fence，用正则兜底提取
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        return json.loads(match.group())

    raise json.JSONDecodeError(
        f"Failed to parse JSON (len={len(content)}): {content[:200]}",
        content, 0,
    )


def _validate_result(result: dict) -> dict:
    """校验并修正 AI 返回结果，确保字段合规。"""
    sentiment = result.get("sentiment", "unrecognizable")
    if sentiment not in VALID_SENTIMENTS:
        sentiment = "unrecognizable"

    content_sentiment = result.get("content_sentiment", sentiment)
    if content_sentiment not in VALID_SENTIMENTS:
        content_sentiment = sentiment

    category = result.get("category", "other")
    if category not in VALID_CATEGORIES:
        category = "other"

    priority = result.get("priority", "无")
    if priority not in VALID_PRIORITIES:
        priority = "无"

    def _parse_tags(raw) -> str:
        if isinstance(raw, list):
            tags = [_normalize_tag(str(t)) for t in raw if str(t).strip()]
        else:
            tags = [_normalize_tag(t) for t in str(raw).split(",") if t.strip()]
        seen: set[str] = set()
        unique = []
        for t in tags:
            if t and t not in seen:
                seen.add(t)
                unique.append(t)
        return ",".join(unique[:3])

    return {
        "sentiment": sentiment,
        "content_sentiment": content_sentiment,
        "category": category,
        "priority": priority,
        "reason": str(result.get("reason", "")),
        "improvement": str(result.get("improvement", "")),
        "issue_tag": _parse_tags(result.get("issue_tags", result.get("issue_tag", []))),
        "highlight_tag": _parse_tags(result.get("highlight_tags", result.get("highlight_tag", []))),
    }


def _make_unrecognizable() -> dict:
    """生成一条 unrecognizable 默认结果。"""
    return {
        "sentiment": "unrecognizable",
        "content_sentiment": "unrecognizable",
        "category": "invalid_garbage",
        "priority": "无",
        "reason": "分析失败",
        "improvement": "",
        "issue_tag": "",
        "highlight_tag": "",
    }


def analyze_comment(
    comment: str,
    category: str,
    api_key: str,
    rating: int | None = None,
    locale: str = "en",
) -> dict:
    """
    单条评论分析：构建 Prompt → 调用 LLM Router → 解析返回。
    返回格式符合 AI 输出字段规范。
    JSON 解析失败时重试 1 次。

    locale="en" 走 GPT-4o-mini 优先链，"zh" 走 DeepSeek 优先链（默认 en，海外优先）。
    api_key 保留用于向后兼容，实际调用走 llm_router（从环境变量读取 Key）。
    """
    prompt = build_prompt(comment, category, rating)

    for attempt in range(2):
        try:
            result = _call_llm(SYSTEM_PROMPT, prompt, locale)
            return _validate_result(result)
        except AuthenticationError:
            raise
        except json.JSONDecodeError:
            if attempt == 0:
                logger.warning("JSON 解析失败，重试中...")
                continue
            logger.error("JSON 解析失败，重试后仍失败")
            return _make_unrecognizable()
        except Exception as e:
            if attempt == 0 and "timeout" not in str(e).lower():
                logger.warning(f"API 调用异常: {e}，重试中...")
                continue
            logger.error(f"API 调用失败: {e}")
            return _make_unrecognizable()

    return _make_unrecognizable()


def _analyze_one(
    index: int,
    item: dict,
    category: str,
    api_key: str,
    locale: str = "en",
) -> tuple[int, dict]:
    """分析单条评论，返回 (索引, 合并结果)。供线程池调用。"""
    content = item.get("content", "").strip()

    if not content:
        return index, {**item, **_make_unrecognizable()}

    rating = item.get("rating")
    if rating is not None:
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            rating = None

    try:
        analysis = analyze_comment(content, category, api_key, rating, locale=locale)
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"第 {index + 1} 条分析失败: {e}")
        analysis = _make_unrecognizable()

    return index, {**item, **analysis}


def analyze_batch(
    comments: list[dict],
    category: str,
    api_key: str,
    progress_callback: callable | None = None,
    max_workers: int = 10,
    locale: str = "en",
) -> list[dict]:
    """
    批量分析，带进度回调。通过 LLM Router 自动 fallback。
    无效 API Key 时抛出异常停止分析。

    comments 中每个 dict 需包含 "content" 字段，可选 "rating" 字段。
    返回列表中每个 dict 包含原始字段 + AI 分析结果字段。

    locale="en" 走 GPT-4o-mini 优先链，"zh" 走 DeepSeek 优先链（默认 en，海外优先）。
    api_key 保留用于向后兼容，实际调用走 llm_router（从环境变量读取 Key）。
    """
    import time

    total = len(comments)
    if total == 0:
        return []

    results: list[dict | None] = [None] * total
    lock = threading.Lock()
    done_count = 0
    auth_error = None

    def on_done(future):
        nonlocal done_count, auth_error
        try:
            idx, merged = future.result()
            results[idx] = merged
        except AuthenticationError:
            auth_error = ValueError("API Key 无效，请检查您的 LLM API Key 设置")
            return
        except Exception as e:
            logger.error(f"并发分析异常: {e}")
            return

        with lock:
            done_count += 1

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, item in enumerate(comments):
            f = executor.submit(_analyze_one, i, item, category, api_key, locale)
            f.add_done_callback(on_done)
            futures.append(f)

        # 主线程轮询进度并回调（确保 Streamlit 组件更新在主线程）
        while done_count < total:
            with lock:
                current = done_count
            if progress_callback and current > 0:
                progress_callback(current, total)
            if auth_error:
                executor.shutdown(wait=False, cancel_futures=True)
                raise auth_error
            time.sleep(0.3)

        # 最后一次回调确保 100%
        if progress_callback:
            progress_callback(total, total)

    for i, r in enumerate(results):
        if r is None:
            results[i] = {**comments[i], **_make_unrecognizable()}

    return results


def extract_tags_from_comments(
    comments: list[dict],
    sentiment_type: str,
) -> dict:
    """
    统计标签出现次数，用于 TOP10 展示。

    sentiment_type: "positive" 或 "negative"
    - positive → 统计 highlight_tag
    - negative → 统计 issue_tag

    返回格式: {"标签名": {"count": 次数, "percentage": 占比}}
    按 count 降序排列。
    """
    tag_field = "highlight_tag" if sentiment_type == "positive" else "issue_tag"
    tag_counts: dict[str, int] = {}

    has_content_count = 0
    for comment in comments:
        content = comment.get("content", "").strip()
        if not content:
            continue
        has_content_count += 1

        raw_tags = comment.get(tag_field, "")
        if not raw_tags:
            continue

        seen_in_comment: set[str] = set()
        for tag in raw_tags.split(","):
            tag = tag.strip()
            if tag and tag not in seen_in_comment:
                seen_in_comment.add(tag)
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    total = has_content_count if has_content_count > 0 else 1

    result = {}
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
        result[tag] = {
            "count": count,
            "percentage": round(count / total * 100, 1),
        }

    return result


def get_api_key(user_id: int | None = None) -> str:
    """
    获取 API Key：优先从数据库 settings 表读取用户自己的 Key，
    fallback 到 .env 系统默认 Key。
    """
    if user_id is not None:
        try:
            from .auth import load_user_api_key
            from .database import get_setting

            user_key = load_user_api_key(user_id)
            if user_key:
                return user_key
            legacy_key = get_setting(user_id, "api_key")
            if legacy_key:
                return legacy_key
        except Exception:
            pass

    env_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not env_key:
        raise ValueError("未配置 API Key，请在设置页面填写您的 DeepSeek API Key")
    return env_key
