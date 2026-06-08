"""V4-T3 worker 通道端到端 smoke 验证.

不写真实 DB，但走完 worker 的所有转换步骤，确认：
1. deep_analyzer.analyze_batch 能调通 DeepSeek 并返回合法 V4 schema
2. category_grouper.aspects_to_legacy_schema 能把 V4 输出转成 legacy 8 字段
3. workers/jobs.py 中的双写合并逻辑产出的字典符合 update_comment_analysis 期望

跑法：
    python3 scripts/smoke_v4t3_worker_chain.py

需要 .env 中配置 DEEPSEEK_API_KEY。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend_api.app.services.category_grouper import aspects_to_legacy_schema
from backend_api.app.services.deep_analyzer import analyze_batch
from backend_api.app.services.prompt_registry import DEFAULT_ANNOTATE_VERSION

ANALYZER_VERSION = "v4_deep"
PROMPT_VERSION = DEFAULT_ANNOTATE_VERSION

SAMPLE_COMMENTS = [
    {
        "content": "Bed frame broke after 2 weeks. Slats snapped under normal weight. Customer service never replied to my emails.",
        "rating": 1,
        "title": "Cheap and unsafe",
    },
    {
        "content": "Beautiful headboard, easy to assemble in 30 minutes. Sturdy and looks exactly like the photos.",
        "rating": 5,
        "title": "Love it",
    },
    {
        "content": "Comfortable but the smell of glue was strong for the first week. Wish it had under-bed storage.",
        "rating": 4,
        "title": "Good but...",
    },
]


def main() -> int:
    print("=" * 80)
    print(f"V4-T3 worker 通道 smoke 验证 (prompt {PROMPT_VERSION}, analyzer {ANALYZER_VERSION})")
    print("=" * 80)

    print("\n[1/3] 调用 deep_analyze_batch (3 条样本评论, sub_category=家具家居)...")
    v4_results = analyze_batch(
        comments=SAMPLE_COMMENTS,
        sub_category="家具家居",
        prompt_version=PROMPT_VERSION,
    )
    if len(v4_results) != len(SAMPLE_COMMENTS):
        print(f"[FAIL] 返回结果数 {len(v4_results)} != 输入 {len(SAMPLE_COMMENTS)}")
        return 1
    print(f"  → 收到 {len(v4_results)} 条 V4 输出")

    print("\n[2/3] 检查 V4 schema 合法 + 应用 aspects_to_legacy_schema 转换...")
    fail_count = 0
    final_records: list[dict] = []
    for i, (comment, v4) in enumerate(zip(SAMPLE_COMMENTS, v4_results), 1):
        print(f"\n  [{i}] {comment['content'][:60]}...")
        if v4.get("error"):
            print(f"      [FAIL] V4 调用失败: {v4['error']}")
            fail_count += 1
            continue

        sentiment = v4.get("sentiment")
        aspects = v4.get("aspects", [])
        pain_points = v4.get("pain_points", [])
        highlights = v4.get("highlights", [])

        print(f"      sentiment={sentiment}")
        aspect_summary = ", ".join(f"{a.get('key')}/{a.get('polarity')}" for a in aspects)
        print(f"      aspects=[{aspect_summary}]")
        print(f"      pain_points={pain_points}")
        print(f"      highlights={highlights}")

        legacy = aspects_to_legacy_schema(
            aspects=aspects,
            sentiment=sentiment or "neutral",
            content=comment.get("content", ""),
            pain_points=pain_points,
            highlights=highlights,
        )
        legacy["aspects_json"] = {
            "sentiment": sentiment,
            "aspects": aspects,
            "pain_points": pain_points,
            "highlights": highlights,
            "evidence_level_overall": v4.get("evidence_level_overall"),
            "prompt_version": v4.get("prompt_version", PROMPT_VERSION),
        }
        legacy["analyzer_version"] = ANALYZER_VERSION

        # 检查 legacy schema 必备字段
        required = {
            "sentiment", "content_sentiment", "category", "priority", "reason",
            "improvement", "issue_tag", "highlight_tag", "aspects_json", "analyzer_version",
        }
        missing = required - legacy.keys()
        if missing:
            print(f"      [FAIL] legacy 缺字段: {missing}")
            fail_count += 1
            continue

        print(f"      → category={legacy['category']}  priority={legacy['priority']}")
        print(f"      → issue_tag={legacy['issue_tag']!r}  highlight_tag={legacy['highlight_tag']!r}")
        print(f"      → analyzer_version={legacy['analyzer_version']}  aspects_json keys={list(legacy['aspects_json'].keys())}")
        final_records.append(legacy)

    print("\n[3/3] 模拟评分覆写（worker 实际逻辑）...")
    for i, (comment, record) in enumerate(zip(SAMPLE_COMMENTS, final_records), 1):
        rating = comment.get("rating")
        if rating is not None:
            try:
                rating_val = int(float(rating))
                final_sentiment = "negative" if rating_val <= 3 else "positive"
                if record.get("sentiment") != final_sentiment:
                    print(f"  [{i}] 评分覆写: rating={rating_val} → sentiment {record.get('sentiment')} → {final_sentiment}")
                record["sentiment"] = final_sentiment
            except (TypeError, ValueError):
                pass

    print("\n" + "=" * 80)
    if fail_count == 0:
        print(f"✅ 端到端 smoke 通过 ({len(final_records)}/{len(SAMPLE_COMMENTS)} 条记录可写入 DB)")
        print("\n第一条记录示例（DB 写入前形态）:")
        if final_records:
            print(json.dumps(final_records[0], ensure_ascii=False, indent=2, default=str))
        return 0
    print(f"❌ smoke 失败：{fail_count}/{len(SAMPLE_COMMENTS)} 条出错")
    return 1


if __name__ == "__main__":
    sys.exit(main())
