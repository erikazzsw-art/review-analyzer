"""category_grouper 单元测试 (Step 2 验收用).

覆盖：
- 19→11 直接映射（category slug）
- aesthetics 边界规则
- 5 派生规则（mixed / simple_praise / invalid_garbage / feature_request / positive_feedback）
- safety 高优先级
- issue_tag / highlight_tag 中文输出
- CATEGORY_SLUGS 白名单：所有 case 输出 category 必须在白名单内

自 V4-M2-2.2.C 起：category 字段全部改英文 slug。
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path so `backend_api.app...` imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend_api.app.services.category_grouper import (
    CATEGORY_SLUGS,
    aspects_to_legacy_schema,
)

TEST_CASES = [
    # (描述, aspects, sentiment, content, pain_points, highlights, 期望 category, 期望 priority)
    (
        "正面+负面混合 (4 星 minor issue)",
        [
            {"key": "ease_of_use", "polarity": "positive", "evidence_span": "Bed works great", "evidence_level": "certain"},
            {"key": "durability", "polarity": "negative", "evidence_span": "bars break", "evidence_level": "certain"},
        ],
        "positive",
        "Bed works great but the bars break easily",
        ["bars break easily"],
        ["bed works great"],
        "mixed",
        "高",
    ),
    (
        "纯负面 (运输损坏 + 客服)",
        [
            {"key": "shipping_damage", "polarity": "negative", "evidence_span": "Bent frame", "evidence_level": "certain"},
            {"key": "customer_service", "polarity": "negative", "evidence_span": "no refund", "evidence_level": "certain"},
        ],
        "negative",
        "It was hard to assemble with bent frame and no refund",
        ["bent frame", "no refund"],
        [],
        "packaging_logistics",
        "高",
    ),
    (
        "纯正面 aesthetics → positive_feedback",
        [
            {"key": "aesthetics", "polarity": "positive", "evidence_span": "looks great", "evidence_level": "certain"},
        ],
        "positive",
        "Beautiful design, looks great",
        [],
        ["looks great"],
        "positive_feedback",
        "无",
    ),
    (
        "aesthetics 负面 → product_quality",
        [
            {"key": "aesthetics", "polarity": "negative", "evidence_span": "ugly color", "evidence_level": "certain"},
        ],
        "negative",
        "The color is ugly and looks cheap",
        ["ugly color"],
        [],
        "product_quality",
        "高",
    ),
    (
        "无 aspects + 单纯好评 → simple_praise",
        [],
        "positive",
        "Great product",
        [],
        [],
        "simple_praise",
        "无",
    ),
    (
        "无效内容 (< 5 字符) → invalid_garbage",
        [],
        "neutral",
        "ok",
        [],
        [],
        "invalid_garbage",
        "无",
    ),
    (
        "功能需求关键词触发 → feature_request",
        [
            {"key": "ease_of_use", "polarity": "neutral", "evidence_span": "I wish it had", "evidence_level": "certain"},
        ],
        "neutral",
        "Wish it had USB charging port",
        [],
        ["wish it had USB"],
        "feature_request",
        "无",
    ),
    (
        "safety 触发高优先级",
        [
            {"key": "safety", "polarity": "negative", "evidence_span": "kid almost fell", "evidence_level": "certain"},
        ],
        "negative",
        "My kid almost fell off this bed",
        ["unsafe edge"],
        [],
        "product_quality",
        "高",
    ),
    (
        "纯负面 build_quality + customer_service → product_quality",
        [
            {"key": "build_quality", "polarity": "negative", "evidence_span": "cheap material", "evidence_level": "certain"},
            {"key": "customer_service", "polarity": "negative", "evidence_span": "no response", "evidence_level": "probable"},
        ],
        "negative",
        "The material is cheap and customer service never responded",
        ["cheap material", "no customer service response"],
        [],
        "product_quality",
        "高",
    ),
]


def main() -> int:
    print("=" * 80)
    print("category_grouper 单元测试")
    print("=" * 80)
    pass_count = 0
    fail_count = 0
    slugs_set = set(CATEGORY_SLUGS)
    for desc, aspects, sentiment, content, pain, highlights, exp_cat, exp_pri in TEST_CASES:
        result = aspects_to_legacy_schema(aspects, sentiment, content, pain, highlights)
        ok_cat = result["category"] == exp_cat
        ok_pri = result["priority"] == exp_pri
        ok_whitelist = result["category"] in slugs_set
        if ok_cat and ok_pri and ok_whitelist:
            pass_count += 1
            print(f"\n[OK] {desc}")
        else:
            fail_count += 1
            print(f"\n[FAIL] {desc}")
        print(f"   category: {result['category']:>20s} (期望: {exp_cat})")
        print(f"   priority: {result['priority']:>10s} (期望: {exp_pri})")
        if not ok_whitelist:
            print("   ❌ category 不在 CATEGORY_SLUGS 白名单内！")
        print(f"   issue_tag: {result['issue_tag']!r}")
        print(f"   highlight_tag: {result['highlight_tag']!r}")
        print(f"   reason: {result['reason']!r}")

    # 额外 snapshot：CATEGORY_SLUGS 白名单必须包含 11 个 slug
    print("\n" + "=" * 80)
    print("白名单 snapshot")
    print("=" * 80)
    expected_slugs = {
        "product_quality", "packaging_logistics", "user_experience",
        "customer_service", "value_for_money", "feature_request",
        "positive_feedback", "simple_praise", "invalid_garbage",
        "mixed", "other",
    }
    if slugs_set == expected_slugs:
        pass_count += 1
        print("[OK] CATEGORY_SLUGS 与 11 类定稿一致")
    else:
        fail_count += 1
        print("[FAIL] CATEGORY_SLUGS 与 11 类定稿不一致")
        print(f"   多余: {slugs_set - expected_slugs}")
        print(f"   缺失: {expected_slugs - slugs_set}")

    print(f"\n{'=' * 80}")
    print(f"测试结果: {pass_count} 通过 / {fail_count} 失败")
    print("=" * 80)
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
