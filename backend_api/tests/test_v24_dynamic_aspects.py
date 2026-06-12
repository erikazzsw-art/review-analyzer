"""V4-T1.5 单元测试：taxonomy 接入分析链路的动态 aspect 注入.

不依赖真实 DB / DeepSeek API；DB 路径通过 monkey patch 模拟。

覆盖：
- taxonomy_loader.render_aspects_block: 多行格式正确
- taxonomy_loader.resolve_aspects: 命中/未命中/DB 异常三种路径
- _validate_annotation: 接受 allowed_aspects 后，能放行 v2.3 不识别的新 key（charging_speed）
- analyze_one: v2.4 prompt + aspects_block 注入 → 占位符消失 + 新 key 被放行
- analyze_one: v2.4 prompt 未传 aspects_block → 自动 fallback（不抛异常 + 占位符替换）
- analyze_one: v2.3 调用方不传 aspects_block 时行为不变（向后兼容）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend_api.app.services import taxonomy_loader
from backend_api.app.services.deep_analyzer import (
    _validate_annotation,
    analyze_one,
)
from backend_api.app.services.prompt_registry import load_prompt
from backend_api.app.services.taxonomy_loader import (
    get_fallback_aspects,
    render_aspects_block,
    resolve_aspects,
)


def _valid_annotation(aspect_key: str = "durability") -> dict:
    return {
        "sentiment": "negative",
        "aspects": [
            {
                "key": aspect_key,
                "polarity": "negative",
                "evidence_span": "broke",
                "evidence_level": "certain",
            }
        ],
        "pain_points": [],
        "highlights": [],
        "evidence_level_overall": "certain",
    }


def _mock_client(payloads: list[str | Exception]) -> tuple[MagicMock, dict]:
    captured = {"messages": []}
    client = MagicMock()
    idx = {"n": 0}

    def _create(**kwargs):
        captured["messages"].append(kwargs.get("messages", []))
        i = idx["n"]
        idx["n"] += 1
        item = payloads[i]
        if isinstance(item, Exception):
            raise item
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = item
        resp.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        return resp

    client.chat.completions.create.side_effect = _create
    return client, captured


# ---------- taxonomy_loader 公共渲染 ----------

def test_render_aspects_block() -> tuple[int, int]:
    p, f = 0, 0
    aspects = [
        {"key": "assembly", "label_zh": "组装难度"},
        {"key": "stability", "label_zh": "稳固性"},
        {"key": "other", "label_zh": "其他"},
    ]
    block = render_aspects_block(aspects)
    expected_lines = [
        "- assembly: 组装难度",
        "- stability: 稳固性",
        "- other: 其他",
    ]
    if block == "\n".join(expected_lines):
        p += 1
        print("[OK]   render_aspects_block 多行格式正确")
    else:
        f += 1
        print(f"[FAIL] render_aspects_block 渲染:\n{block!r}")

    # fallback 至少有 9 项核心 + other = 10 项
    fb = get_fallback_aspects()
    if len(fb) == 10 and fb[-1]["key"] == "other":
        p += 1
        print("[OK]   fallback base 块包含 10 项且 other 在末尾")
    else:
        f += 1
        print(f"[FAIL] fallback base 块: len={len(fb)}, last={fb[-1] if fb else None}")
    return p, f


# ---------- resolve_aspects 三种路径 ----------

def test_resolve_aspects_paths() -> tuple[int, int]:
    p, f = 0, 0
    taxonomy_loader.clear_cache()

    # Path 1: DB 命中 → 返回 taxonomy 行
    mock_rows = (("assembly", "组装难度"), ("stability", "稳固性"), ("durability", "耐用性"))

    def fake_db_hit(sub):
        return mock_rows

    taxonomy_loader._load_aspects_from_db = fake_db_hit  # type: ignore[assignment]
    aspects, hit = resolve_aspects("床架")
    keys = [a["key"] for a in aspects]
    if hit and keys == ["assembly", "stability", "durability", "other"]:
        p += 1
        print("[OK]   resolve_aspects DB 命中 + other 自动追加")
    else:
        f += 1
        print(f"[FAIL] DB 命中路径: hit={hit} keys={keys}")

    # Path 2: DB 未命中（返回空元组）→ fallback
    def fake_db_miss(sub):
        return ()

    taxonomy_loader._load_aspects_from_db = fake_db_miss  # type: ignore[assignment]
    aspects, hit = resolve_aspects("户外帐篷")
    keys = [a["key"] for a in aspects]
    if not hit and len(keys) == 10 and keys[-1] == "other":
        p += 1
        print("[OK]   resolve_aspects DB 未命中 → fallback base 块")
    else:
        f += 1
        print(f"[FAIL] fallback 路径: hit={hit} keys={keys}")

    # Path 3: 空字符串 sub_category → fallback（_load_aspects_from_db 早 return）
    aspects, hit = resolve_aspects("")
    if not hit and len(aspects) == 10:
        p += 1
        print("[OK]   resolve_aspects 空 sub_category → fallback")
    else:
        f += 1
        print(f"[FAIL] 空 sub_category: hit={hit} len={len(aspects)}")

    # Path 4: taxonomy 表里已经含 other → 不重复追加
    def fake_db_with_other(sub):
        return (("comfort", "舒适度"), ("other", "其他"))

    taxonomy_loader._load_aspects_from_db = fake_db_with_other  # type: ignore[assignment]
    aspects, hit = resolve_aspects("床垫")
    other_count = sum(1 for a in aspects if a["key"] == "other")
    if hit and other_count == 1 and aspects[-1]["key"] == "other":
        p += 1
        print("[OK]   resolve_aspects 表已含 other → 不重复且固定末尾")
    else:
        f += 1
        print(f"[FAIL] other 去重: aspects={[a['key'] for a in aspects]}")

    return p, f


# ---------- _validate_annotation 接受 allowed_aspects ----------

def test_validate_with_allowed_aspects() -> tuple[int, int]:
    p, f = 0, 0

    # 默认行为：charging_speed 不在 ASPECT_KEYS → 拒绝
    obj = _valid_annotation("charging_speed")
    ok, err = _validate_annotation(obj)
    if not ok and "key_invalid" in err:
        p += 1
        print("[OK]   默认校验拒绝 charging_speed（v2.3 兼容）")
    else:
        f += 1
        print(f"[FAIL] 默认校验应拒绝 charging_speed: ok={ok} err={err}")

    # 传入动态闭合集 → 放行
    ok, err = _validate_annotation(obj, allowed_aspects={"charging_speed", "other"})
    if ok:
        p += 1
        print("[OK]   传入 allowed_aspects={charging_speed,...} → 放行")
    else:
        f += 1
        print(f"[FAIL] 动态闭合集放行失败: err={err}")

    # 动态闭合集不含 durability → 拒绝（即使 durability 在 ASPECT_KEYS）
    obj2 = _valid_annotation("durability")
    ok, err = _validate_annotation(obj2, allowed_aspects={"charging_speed", "other"})
    if not ok and "key_invalid" in err:
        p += 1
        print("[OK]   动态闭合集排除 durability → 即使 ASPECT_KEYS 有也拒绝")
    else:
        f += 1
        print(f"[FAIL] 动态闭合集排除验证: ok={ok}")

    return p, f


# ---------- analyze_one + v2.4 占位符注入 ----------

def test_analyze_one_v24_placeholder_replaced() -> tuple[int, int]:
    p, f = 0, 0

    aspects_block = "- charging_speed: 充电速度\n- battery_life: 续航\n- other: 其他"
    allowed = ["charging_speed", "battery_life", "other"]
    client, captured = _mock_client([json.dumps(_valid_annotation("charging_speed"))])

    r = analyze_one(
        content="Charges slowly",
        rating=2,
        sub_category="充电器",
        client=client,
        prompt_version="v2.4",
        aspects_block=aspects_block,
        allowed_aspects=allowed,
    )

    if r.get("error") is None and r.get("aspects", [{}])[0].get("key") == "charging_speed":
        p += 1
        print("[OK]   v2.4 + 3C aspects_block 注入 → charging_speed 被放行")
    else:
        f += 1
        print(f"[FAIL] v2.4 注入: r={r}")

    sys_msg = captured["messages"][0][0]["content"]
    if "{{ASPECTS_BLOCK}}" not in sys_msg and "charging_speed: 充电速度" in sys_msg:
        p += 1
        print("[OK]   v2.4 system prompt 中占位符已替换为实际 aspect 列表")
    else:
        f += 1
        print(
            f"[FAIL] 占位符替换检查: placeholder_left={'{{ASPECTS_BLOCK}}' in sys_msg} "
            f"charging_speed_present={'charging_speed' in sys_msg}"
        )

    return p, f


def test_analyze_one_v24_auto_fallback() -> tuple[int, int]:
    """v2.4 但调用方没传 aspects_block → 自动用 fallback，不抛异常."""
    p, f = 0, 0

    client, captured = _mock_client([json.dumps(_valid_annotation("durability"))])
    r = analyze_one(
        content="x",
        rating=3,
        sub_category="家具家居",
        client=client,
        prompt_version="v2.4",
    )

    sys_msg = captured["messages"][0][0]["content"]
    if "{{ASPECTS_BLOCK}}" not in sys_msg and r.get("error") is None:
        p += 1
        print("[OK]   v2.4 不传 aspects_block → 自动 fallback 块注入 + 不抛异常")
    else:
        f += 1
        print(f"[FAIL] v2.4 auto-fallback: error={r.get('error')} placeholder_left={'{{ASPECTS_BLOCK}}' in sys_msg}")

    return p, f


def test_analyze_one_v23_backward_compat() -> tuple[int, int]:
    """v2.3 调用方不传新参数 → 行为完全不变."""
    p, f = 0, 0

    client, captured = _mock_client([json.dumps(_valid_annotation("durability"))])
    r = analyze_one(
        content="x",
        rating=3,
        sub_category="家具家居",
        client=client,
        prompt_version="v2.3",
    )

    sys_msg = captured["messages"][0][0]["content"]
    if r.get("error") is None and "{{ASPECTS_BLOCK}}" not in sys_msg and "ASPECT TAXONOMY (closed list of 19 keys" in sys_msg:
        p += 1
        print("[OK]   v2.3 向后兼容：不传新参数 → 走原硬编码 19 类 prompt")
    else:
        f += 1
        print(f"[FAIL] v2.3 向后兼容: error={r.get('error')}")

    return p, f


# ---------- prompt 模板加载完整性 ----------

def test_v24_prompt_loadable() -> tuple[int, int]:
    p, f = 0, 0
    try:
        pd = load_prompt("annotate", "v2.4")
        if "{{ASPECTS_BLOCK}}" in pd.system_prompt:
            p += 1
            print("[OK]   load_prompt('annotate','v2.4') 成功且占位符存在")
        else:
            f += 1
            print("[FAIL] v2.4 prompt 文件加载后未发现占位符")
    except Exception as e:
        f += 1
        print(f"[FAIL] load_prompt('annotate','v2.4') 异常: {e}")
    return p, f


# ---------- main ----------

def main() -> int:
    print("=" * 80)
    print("V4-T1.5 taxonomy 注入分析链路 单元测试")
    print("=" * 80)

    suites = [
        ("render_aspects_block / fallback", test_render_aspects_block),
        ("resolve_aspects 三路径", test_resolve_aspects_paths),
        ("_validate_annotation allowed_aspects", test_validate_with_allowed_aspects),
        ("analyze_one v2.4 注入路径", test_analyze_one_v24_placeholder_replaced),
        ("analyze_one v2.4 auto-fallback", test_analyze_one_v24_auto_fallback),
        ("analyze_one v2.3 向后兼容", test_analyze_one_v23_backward_compat),
        ("v2.4 prompt 文件加载", test_v24_prompt_loadable),
    ]
    total_p, total_f = 0, 0
    for name, fn in suites:
        print(f"\n— {name} —")
        cp, cf = fn()
        total_p += cp
        total_f += cf

    print("\n" + "=" * 80)
    print(f"测试结果: {total_p} 通过 / {total_f} 失败")
    print("=" * 80)
    return 0 if total_f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
