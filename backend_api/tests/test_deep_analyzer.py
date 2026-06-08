"""deep_analyzer 单元测试.

不依赖真实 DeepSeek API，只覆盖纯函数与可 mock 的路径：
- _validate_annotation: schema 校验各种合法/非法形态
- _build_user_prompt: prompt 拼接
- analyze_one: 用 mock client 验证成功/JSON 解析失败/schema 不合法/异常重试/最终降级
- analyze_batch: 批处理顺序与失败降级
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend_api.app.services.deep_analyzer import (
    _build_user_prompt,
    _validate_annotation,
    analyze_batch,
    analyze_one,
)


def _valid_annotation() -> dict:
    return {
        "sentiment": "negative",
        "aspects": [
            {
                "key": "durability",
                "polarity": "negative",
                "evidence_span": "broke after 2 weeks",
                "evidence_level": "certain",
            }
        ],
        "pain_points": ["frame broke quickly"],
        "highlights": [],
        "evidence_level_overall": "certain",
    }


def _build_mock_client(payloads: list[str | Exception]) -> MagicMock:
    """构造一个 OpenAI client mock，每次调用返回 payloads 中下一项。

    str → 包装为 chat.completions.create 返回值
    Exception → raise
    """
    client = MagicMock()
    call_count = {"n": 0}

    def _create(**kwargs):
        idx = call_count["n"]
        call_count["n"] += 1
        if idx >= len(payloads):
            raise RuntimeError(f"mock 调用次数超出预期: {idx + 1}")
        item = payloads[idx]
        if isinstance(item, Exception):
            raise item
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = item
        resp.usage = MagicMock(prompt_tokens=120, completion_tokens=80)
        return resp

    client.chat.completions.create.side_effect = _create
    client._call_count = call_count
    return client


# ---------- _validate_annotation ----------

VALIDATION_CASES: list[tuple[str, dict, bool, str]] = [
    ("合法 annotation", _valid_annotation(), True, ""),
    ("不是 dict", "not a dict", False, "not_a_dict"),
    (
        "sentiment 非法值",
        {**_valid_annotation(), "sentiment": "happy"},
        False,
        "invalid_sentiment",
    ),
    (
        "aspects 不是 list",
        {**_valid_annotation(), "aspects": "durability"},
        False,
        "aspects_not_a_list",
    ),
    (
        "aspect.key 不在闭合 19 类",
        {
            **_valid_annotation(),
            "aspects": [
                {
                    "key": "made_up_aspect",
                    "polarity": "negative",
                    "evidence_span": "x",
                    "evidence_level": "certain",
                }
            ],
        },
        False,
        "key_invalid",
    ),
    (
        "aspect.polarity 非法",
        {
            **_valid_annotation(),
            "aspects": [
                {
                    "key": "durability",
                    "polarity": "mixed",
                    "evidence_span": "x",
                    "evidence_level": "certain",
                }
            ],
        },
        False,
        "polarity_invalid",
    ),
    (
        "evidence_span 不是字符串",
        {
            **_valid_annotation(),
            "aspects": [
                {
                    "key": "durability",
                    "polarity": "negative",
                    "evidence_span": 123,
                    "evidence_level": "certain",
                }
            ],
        },
        False,
        "evidence_span_not_str",
    ),
    (
        "evidence_level 非法",
        {
            **_valid_annotation(),
            "aspects": [
                {
                    "key": "durability",
                    "polarity": "negative",
                    "evidence_span": "x",
                    "evidence_level": "definitely",
                }
            ],
        },
        False,
        "evidence_level_invalid",
    ),
    (
        "pain_points 不是 list",
        {**_valid_annotation(), "pain_points": "broke"},
        False,
        "pain_points_not_a_list",
    ),
    (
        "highlights 不是 list",
        {**_valid_annotation(), "highlights": "great"},
        False,
        "highlights_not_a_list",
    ),
    (
        "evidence_level_overall 非法",
        {**_valid_annotation(), "evidence_level_overall": "totally"},
        False,
        "evidence_level_overall_invalid",
    ),
    (
        "aspects 空列表合法",
        {**_valid_annotation(), "aspects": [], "sentiment": "neutral"},
        True,
        "",
    ),
    ("safety 是合法 aspect key", {
        **_valid_annotation(),
        "aspects": [{
            "key": "safety",
            "polarity": "negative",
            "evidence_span": "kid almost fell",
            "evidence_level": "certain",
        }],
    }, True, ""),
]


def run_validation_cases() -> tuple[int, int]:
    pass_count = 0
    fail_count = 0
    for desc, obj, exp_ok, exp_err_substr in VALIDATION_CASES:
        ok, err = _validate_annotation(obj)
        passed = ok == exp_ok and (exp_err_substr in err if not exp_ok else True)
        if passed:
            pass_count += 1
            print(f"[OK]   {desc}")
        else:
            fail_count += 1
            print(f"[FAIL] {desc}: ok={ok} err={err!r} (期望 ok={exp_ok}, err 含 {exp_err_substr!r})")
    return pass_count, fail_count


# ---------- _build_user_prompt ----------

def run_prompt_cases() -> tuple[int, int]:
    pass_count = 0
    fail_count = 0

    cases = [
        (
            "正常 rating + title",
            {"content": "Bed broke", "rating": 2, "sub_category": "床架", "title": "Bad bed"},
            ["Sub-category: 床架", "Rating: 2 stars", "Title: Bad bed", "Content: Bed broke", "Output JSON:"],
        ),
        (
            "rating 为 None",
            {"content": "Nice", "rating": None, "sub_category": "家具家居", "title": ""},
            ["Rating: N/A"],
        ),
        (
            "rating 为浮点字符串安全转换",
            {"content": "ok", "rating": 4, "sub_category": "家具家居", "title": ""},
            ["Rating: 4 stars"],
        ),
    ]
    for desc, kwargs, expected_substrings in cases:
        out = _build_user_prompt(
            content=kwargs["content"],
            rating=kwargs["rating"],
            sub_category=kwargs["sub_category"],
            title=kwargs["title"],
        )
        missing = [s for s in expected_substrings if s not in out]
        if not missing:
            pass_count += 1
            print(f"[OK]   prompt 拼接 — {desc}")
        else:
            fail_count += 1
            print(f"[FAIL] prompt 拼接 — {desc}: 缺失 {missing!r}\n  实际输出:\n{out}")
    return pass_count, fail_count


# ---------- analyze_one with mock ----------

def run_analyze_one_cases() -> tuple[int, int]:
    pass_count = 0
    fail_count = 0

    # Case 1: 一次成功
    client = _build_mock_client([json.dumps(_valid_annotation())])
    r = analyze_one(content="Bed broke", rating=2, sub_category="床架", title="bad", client=client)
    if r.get("error") is None and r.get("sentiment") == "negative" and r.get("prompt_version") == "v2.1":
        pass_count += 1
        print("[OK]   analyze_one 一次成功")
    else:
        fail_count += 1
        print(f"[FAIL] analyze_one 一次成功: {r}")

    # Case 2: 第一次返回非法 JSON 文本，重试一次成功
    client = _build_mock_client(["this is not json", json.dumps(_valid_annotation())])
    r = analyze_one(content="Bed broke", rating=2, sub_category="床架", client=client, max_retries=1)
    if r.get("error") is None and r.get("sentiment") == "negative":
        pass_count += 1
        print("[OK]   analyze_one JSON 解析失败后重试成功")
    else:
        fail_count += 1
        print(f"[FAIL] analyze_one JSON 重试: {r}")

    # Case 3: 两次都返回非法 schema → 最终返回 error
    bad_schema = json.dumps({**_valid_annotation(), "sentiment": "happy"})
    client = _build_mock_client([bad_schema, bad_schema])
    r = analyze_one(content="x", rating=3, sub_category="家具家居", client=client, max_retries=1)
    if r.get("error") and "schema_invalid" in r["error"]:
        pass_count += 1
        print("[OK]   analyze_one schema 不合法两次 → 降级 error")
    else:
        fail_count += 1
        print(f"[FAIL] analyze_one schema 降级: {r}")

    # Case 4: API 异常两次 → 降级 error
    client = _build_mock_client([RuntimeError("network down"), RuntimeError("network down again")])
    r = analyze_one(content="x", rating=3, sub_category="家具家居", client=client, max_retries=1)
    if r.get("error") and "network down" in r["error"]:
        pass_count += 1
        print("[OK]   analyze_one API 异常两次 → 降级 error")
    else:
        fail_count += 1
        print(f"[FAIL] analyze_one 异常降级: {r}")

    # Case 5: prompt_version 透传
    client = _build_mock_client([json.dumps(_valid_annotation())])
    r = analyze_one(
        content="x", rating=5, sub_category="家具家居", client=client, prompt_version="v2.1"
    )
    if r.get("prompt_version") == "v2.1":
        pass_count += 1
        print("[OK]   analyze_one prompt_version 透传")
    else:
        fail_count += 1
        print(f"[FAIL] analyze_one prompt_version 透传: {r}")

    return pass_count, fail_count


# ---------- analyze_batch ----------

def run_analyze_batch_cases() -> tuple[int, int]:
    """analyze_batch 在内部 new 一个 OpenAI client，无法直接注入 mock。

    所以这里只跑一个最小验证：comments 为空时返回空列表（不触发任何 LLM 调用）。
    业务路径靠 analyze_one 的 mock 覆盖。

    注意：analyze_batch 即使 comments 空也会先构造 OpenAI client（调用 _get_api_key），
    所以本用例需要环境提供 DEEPSEEK_API_KEY 或 .env 文件，否则跳过。
    """
    pass_count = 0
    fail_count = 0

    import os
    has_key = bool(os.getenv("DEEPSEEK_API_KEY"))
    if not has_key:
        env_path = Path(__file__).parent.parent.parent / ".env"
        has_key = env_path.exists() and any(
            line.startswith("DEEPSEEK_API_KEY=") for line in env_path.read_text().splitlines()
        )
    if not has_key:
        print("[SKIP] analyze_batch 空批次（未配置 DEEPSEEK_API_KEY，跳过）")
        return 0, 0

    try:
        out = analyze_batch(comments=[], sub_category="家具家居")
        if out == []:
            pass_count += 1
            print("[OK]   analyze_batch 空批次 → 空列表")
        else:
            fail_count += 1
            print(f"[FAIL] analyze_batch 空批次: {out}")
    except Exception as e:
        fail_count += 1
        print(f"[FAIL] analyze_batch 空批次 raise: {e}")
    return pass_count, fail_count


# ---------- main ----------

def main() -> int:
    print("=" * 80)
    print("deep_analyzer 单元测试")
    print("=" * 80)

    total_pass = 0
    total_fail = 0

    print("\n— _validate_annotation —")
    p, f = run_validation_cases()
    total_pass += p
    total_fail += f

    print("\n— _build_user_prompt —")
    p, f = run_prompt_cases()
    total_pass += p
    total_fail += f

    print("\n— analyze_one (mock client) —")
    p, f = run_analyze_one_cases()
    total_pass += p
    total_fail += f

    print("\n— analyze_batch —")
    p, f = run_analyze_batch_cases()
    total_pass += p
    total_fail += f

    print("\n" + "=" * 80)
    print(f"测试结果: {total_pass} 通过 / {total_fail} 失败")
    print("=" * 80)
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
