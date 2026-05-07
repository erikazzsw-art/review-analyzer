"""AI 分析核心 — 跨境电商评论分析"""

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from openai import AuthenticationError, OpenAI

from .config import CATEGORY_TAGS, DEFAULT_CATEGORY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位拥有 6 年跨境电商运营经验的评论分析专家。你的任务是对用户评论进行深度分析，输出结构化 JSON。

## 核心能力
- 理解差评背后的本质问题（包装、物流、安装、质量、功能、客服）
- 好评也提取亮点标签
- 输出必须是可落地的改进建议（不是空话套话）

## 标签标准化约束
- 相似问题统一用同一标签（"包装破损""盒子压扁""运输损坏" → 统一输出"包装破损"）
- 每条评论最多 2 个标签，逗号分隔
- 优先从预设标签库选择，没有合适的再新建
- 标签必须是 2-5 字名词短语

## 分类规则（针对实体商品）
- 产品质量：材质差、做工粗糙、尺寸偏差、颜色差异、功能失效、不耐用、异味等
- 包装物流：包装破损、物流慢、配送问题
- 使用体验：安装困难、操作复杂、设计不合理、使用不方便
- 客服售后：客服态度差、回复慢、退换货麻烦
- 性价比：价格偏高、不值这个价
- 功能需求：缺少某功能、希望改进（差评时使用）
- 正面反馈：质量好、物流快、服务好、性价比高（好评时使用）
- 单纯好评：只有评分无实质内容，或只说"不错""可以"
- 无效乱码：乱码或无意义内容
- 其他：无法归类

## 优先级判定
- 高：严重质量问题、安全隐患、大量用户反馈的共性问题
- 中：影响使用体验但不致命的问题
- 低：个别用户的主观偏好、轻微瑕疵
- 无：好评或无效内容

## 输出格式（严格 JSON）
{
  "sentiment": "positive / negative / neutral / unrecognizable",
  "category": "产品质量 / 包装物流 / 使用体验 / 客服售后 / 性价比 / 功能需求 / 正面反馈 / 单纯好评 / 无效乱码 / 其他",
  "priority": "高 / 中 / 低 / 无",
  "reason": "一句话理由",
  "improvement": "可落地的改进建议",
  "issue_tag": "差评时填写，好评时为空字符串",
  "highlight_tag": "好评时填写，差评时为空字符串"
}"""

VALID_SENTIMENTS = {"positive", "negative", "neutral", "unrecognizable"}
VALID_CATEGORIES = {
    "产品质量", "包装物流", "使用体验", "客服售后", "性价比",
    "功能需求", "正面反馈", "单纯好评", "无效乱码", "其他",
}
VALID_PRIORITIES = {"高", "中", "低", "无"}


def classify_sentiment_by_rating(rating: Optional[int]) -> Optional[str]:
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
    rating: Optional[int] = None,
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


def _call_deepseek_api(prompt: str, api_key: str) -> dict:
    """调用 DeepSeek API，超时 30 秒，返回解析后的 JSON dict。"""
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        timeout=30.0,
    )

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content.strip()
    return json.loads(content)


def _validate_result(result: dict) -> dict:
    """校验并修正 AI 返回结果，确保字段合规。"""
    sentiment = result.get("sentiment", "unrecognizable")
    if sentiment not in VALID_SENTIMENTS:
        sentiment = "unrecognizable"

    category = result.get("category", "其他")
    if category not in VALID_CATEGORIES:
        category = "其他"

    priority = result.get("priority", "无")
    if priority not in VALID_PRIORITIES:
        priority = "无"

    return {
        "sentiment": sentiment,
        "category": category,
        "priority": priority,
        "reason": str(result.get("reason", "")),
        "improvement": str(result.get("improvement", "")),
        "issue_tag": str(result.get("issue_tag", "")),
        "highlight_tag": str(result.get("highlight_tag", "")),
    }


def _make_unrecognizable() -> dict:
    """生成一条 unrecognizable 默认结果。"""
    return {
        "sentiment": "unrecognizable",
        "category": "无效乱码",
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
    rating: Optional[int] = None,
) -> dict:
    """
    单条评论分析：构建 Prompt → 调用 API → 解析返回。
    返回格式符合 AI 输出字段规范。
    JSON 解析失败时重试 1 次。
    """
    prompt = build_prompt(comment, category, rating)

    for attempt in range(2):
        try:
            result = _call_deepseek_api(prompt, api_key)
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
        analysis = analyze_comment(content, category, api_key, rating)
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
    progress_callback: Optional[callable] = None,
    max_workers: int = 10,
) -> list[dict]:
    """
    批量分析，带进度回调。并发调用 DeepSeek API 提升性能。
    无效 API Key 时抛出异常停止分析。

    comments 中每个 dict 需包含 "content" 字段，可选 "rating" 字段。
    返回列表中每个 dict 包含原始字段 + AI 分析结果字段。
    """
    total = len(comments)
    if total == 0:
        return []

    results: list[Optional[dict]] = [None] * total
    lock = threading.Lock()
    done_count = 0
    auth_error = None

    def on_done(future):
        nonlocal done_count, auth_error
        try:
            idx, merged = future.result()
            results[idx] = merged
        except AuthenticationError:
            auth_error = ValueError("API Key 无效，请检查您的 DeepSeek API Key 设置")
            return
        except Exception as e:
            logger.error(f"并发分析异常: {e}")
            return

        with lock:
            done_count += 1
            current = done_count
        if progress_callback:
            progress_callback(current, total)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, item in enumerate(comments):
            f = executor.submit(_analyze_one, i, item, category, api_key)
            f.add_done_callback(on_done)
            futures.append(f)

        for f in futures:
            f.result(timeout=120)
            if auth_error:
                executor.shutdown(wait=False, cancel_futures=True)
                raise auth_error

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

        for tag in raw_tags.split(","):
            tag = tag.strip()
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    total = has_content_count if has_content_count > 0 else 1

    result = {}
    for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
        result[tag] = {
            "count": count,
            "percentage": round(count / total * 100, 1),
        }

    return result


def get_api_key(user_id: Optional[int] = None) -> str:
    """
    获取 API Key：优先从数据库 settings 表读取用户自己的 Key，
    fallback 到 .env 系统默认 Key。
    """
    if user_id is not None:
        try:
            from .database import get_setting

            user_key = get_setting(user_id, "api_key")
            if user_key:
                return user_key
        except Exception:
            pass

    env_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not env_key:
        raise ValueError("未配置 API Key，请在设置页面填写您的 DeepSeek API Key")
    return env_key
