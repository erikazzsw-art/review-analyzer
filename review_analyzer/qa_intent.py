"""问评论意图分类。

规则前置命中即返（0ms 开销），未命中默认走 specific_retrieval（等同今天效果，永不阻塞）。
LLM few-shot 兜底 P1 再接入。
"""

from __future__ import annotations

import re
from typing import TypedDict

INTENT_AGGREGATE_FEEDBACK = "aggregate_feedback"
INTENT_PRODUCT_COMPARE = "product_compare"
INTENT_RATING_BREAKDOWN = "rating_breakdown"
INTENT_CONSUMER_INSIGHT = "consumer_insight"
INTENT_TREND_AND_EMERGING = "trend_and_emerging"
INTENT_SPECIFIC_RETRIEVAL = "specific_retrieval"
INTENT_UNANSWERABLE = "unanswerable"


class IntentResult(TypedDict):
    intent: str
    confidence: float
    slots: dict[str, str]  # 例如 {"polarity": "positive" | "negative"}
    source: str  # "rule" | "llm" | "default"


# 顺序敏感：先命中先返回。compare 类比 aggregate 更强（"哪个产品/A vs B"应优先归为对比）。
_RULE_PATTERNS: list[tuple[str, list[str], dict[str, str]]] = [
    # ── product_compare ──────────────────────────────────────────────
    (
        INTENT_PRODUCT_COMPARE,
        [
            r"哪(个|款|种)产品",
            r"哪(个|款|种).{0,4}(评价|表现|质量|口碑|销量)",
            r"不同产品",
            r"跨产品",
            r"共同(的)?(问题|优点|缺点|差评|好评)",
            r"[A-Za-z0-9一-鿿]+\s*(vs|VS|对比|比较)\s*[A-Za-z0-9一-鿿]+",
        ],
        {},
    ),
    # ── rating_breakdown ─────────────────────────────────────────────
    (
        INTENT_RATING_BREAKDOWN,
        [
            r"[1-5]\s*星",
            r"不同(星级|评分)",
            r"高分.{0,4}(买家|用户|评论)",
            r"低分.{0,4}(买家|用户|评论)",
            r"(差评|好评).{0,4}(买家|用户)",
        ],
        {},
    ),
    # ── trend_and_emerging ───────────────────────────────────────────
    (
        INTENT_TREND_AND_EMERGING,
        [
            r"(最近|近期|近几个月|这段时间).{0,6}(变化|趋势|新出现)",
            r"新(出现|冒出|涌现).{0,4}(问题|痛点|抱怨)",
            r"(满意度|情感|口碑).{0,4}(趋势|变化)",
            r"未被满足",
        ],
        {},
    ),
    # ── consumer_insight ─────────────────────────────────────────────
    (
        INTENT_CONSUMER_INSIGHT,
        [
            r"(主要)?(消费)?(人群|买家群体|画像)",
            r"什么(样的)?(人|买家|用户)在(买|购买|使用)",
            r"(使用|应用)(场景|情境)",
            r"(在|于).{0,4}(什么|哪些)场景",
            r"(购买|下单).{0,4}(动机|理由|原因)",
        ],
        {},
    ),
    # ── aggregate_feedback（好评方向）─────────────────────────────────
    (
        INTENT_AGGREGATE_FEEDBACK,
        [
            r"最(常|多)(提到的|被提到的)?(优点|亮点|好处|好评)",
            r"(优点|亮点|好评).{0,4}有哪些",
            r"最(喜欢|满意|欣赏)",
            r"买家.{0,6}(称赞|赞美|表扬)",
        ],
        {"polarity": "positive"},
    ),
    # ── aggregate_feedback（差评方向）─────────────────────────────────
    (
        INTENT_AGGREGATE_FEEDBACK,
        [
            r"最(常|多)(见|遇到)?的?(差评|投诉|抱怨|问题|痛点|缺点)",
            r"(差评|问题|缺点|抱怨).{0,4}(原因|有哪些|是什么)",
            r"最(不满|讨厌|抵触)",
            r"(改进|优化|期望).{0,4}(哪些|什么|地方)",
            r"(希望|期待).{0,4}改进",
        ],
        {"polarity": "negative"},
    ),
]


def classify_intent(
    question: str,
    products_meta: list[dict] | None = None,  # noqa: ARG001  P1 接入 LLM 时使用
    history: list[dict] | None = None,  # noqa: ARG001  P1 接入 LLM 时使用
) -> IntentResult:
    """基于规则做意图分类。未命中一律返回 specific_retrieval（现有 hybrid 检索流程）。"""
    text = (question or "").strip()
    if not text:
        return {
            "intent": INTENT_SPECIFIC_RETRIEVAL,
            "confidence": 0.0,
            "slots": {},
            "source": "default",
        }

    for intent, patterns, slots in _RULE_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text):
                return {
                    "intent": intent,
                    "confidence": 0.9,
                    "slots": dict(slots),
                    "source": "rule",
                }

    return {
        "intent": INTENT_SPECIFIC_RETRIEVAL,
        "confidence": 0.5,
        "slots": {},
        "source": "default",
    }
