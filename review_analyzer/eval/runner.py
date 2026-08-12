"""单个 prompt 版本在 Golden Set 上的评测器.

核心能力：
- evaluate(prompt_version, golden_set_version) → EvalResult
  跑完整的 LLM 调用 + 准确率统计 + 子集（bad case / 高评分 / 中评分）分析
- 输出指标：sentiment_accuracy / bad_case_accuracy / token_cost
- 失败容错：单条调用失败不中断，记录 ok=False
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from backend_api.app.services.prompt_registry import load_prompt
from backend_api.app.services.taxonomy_loader import (
    render_aspects_block,
    resolve_aspects,
)
from review_analyzer.router_client import OpenAI

from .golden_set import load_golden_set

MODEL = "router"
BASE_URL = ""
MAX_WORKERS = 8

INPUT_PRICE_PER_M = 1.0
OUTPUT_PRICE_PER_M = 8.0


@dataclass
class EvalResult:
    """单个 prompt 版本的评测结果."""
    prompt_version: str
    golden_set_version: str
    n_samples: int
    sentiment_accuracy: float
    bad_case_accuracy: float
    high_rating_accuracy: float
    mid_rating_accuracy: float
    tokens_in: int
    tokens_out: int
    cost_yuan: float
    elapsed_seconds: float
    raw_results: pd.DataFrame = field(repr=False)
    n_call_failures: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_version": self.prompt_version,
            "golden_set_version": self.golden_set_version,
            "n_samples": self.n_samples,
            "sentiment_accuracy": round(self.sentiment_accuracy, 4),
            "bad_case_accuracy": round(self.bad_case_accuracy, 4),
            "high_rating_accuracy": round(self.high_rating_accuracy, 4),
            "mid_rating_accuracy": round(self.mid_rating_accuracy, 4),
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_yuan": round(self.cost_yuan, 6),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "n_call_failures": self.n_call_failures,
        }


def _get_api_key() -> str:
    """读取 llm_router 实际使用的 OPENAI_API_KEY（2026-08 已从 DeepSeek 迁移到 OpenAI+Gemini 双模型链）."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("OPENAI_API_KEY 未配置（llm_router 需要此环境变量）")


def _resolve_system_prompt(base_prompt: str, sub_category: str) -> str:
    """替换 {{ASPECTS_BLOCK}} 占位符（v2.4+）."""
    if "{{ASPECTS_BLOCK}}" not in base_prompt:
        return base_prompt
    aspects, _ = resolve_aspects(sub_category)
    block = render_aspects_block(aspects)
    return base_prompt.replace("{{ASPECTS_BLOCK}}", block)


def _call_llm(client: OpenAI, system_prompt: str, row: pd.Series) -> dict[str, Any]:
    resolved_prompt = _resolve_system_prompt(system_prompt, row.get("sub_category", ""))
    user_msg = (
        f"Sub-category: {row['sub_category']}\n"
        f"Rating: {int(row['rating'])} stars\n"
        f"Title: {row.get('title', '') or ''}\n"
        f"Content: {row['content']}\n\n"
        f"Output JSON:"
    )
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": resolved_prompt},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=800,
        )
        raw = resp.choices[0].message.content
        obj = json.loads(raw)
        return {
            "review_id": row["review_id"],
            "ok": True,
            "sentiment": obj.get("sentiment", ""),
            "tokens_in": resp.usage.prompt_tokens,
            "tokens_out": resp.usage.completion_tokens,
        }
    except Exception as e:
        return {
            "review_id": row["review_id"],
            "ok": False,
            "sentiment": "",
            "tokens_in": 0,
            "tokens_out": 0,
            "error": str(e)[:200],
        }


def evaluate(
    prompt_version: str = "v2.1",
    golden_set_version: str = "v1.0",
    category: str | None = None,
    max_workers: int = MAX_WORKERS,
    progress_callback: Any = None,
) -> EvalResult:
    """在 Golden Set 上评测指定 prompt 版本.

    Args:
        prompt_version: backend_api/app/prompts/annotate_v{version}.md
        golden_set_version: data/golden_set/{version}/
        category: 品类子目录名（仅 v1.1+ 适用，如 'pet', '3c'）
        max_workers: 并发线程数
        progress_callback: 可选回调 (done, total) → None

    Returns:
        EvalResult 含准确率 / token / 成本指标
    """
    prompt_def = load_prompt("annotate", prompt_version)
    df = load_golden_set(golden_set_version, category=category)
    n = len(df)
    if n == 0:
        raise RuntimeError(f"Golden Set {golden_set_version} 为空，无法评测")

    client = OpenAI(api_key=_get_api_key(), base_url=BASE_URL, timeout=30.0)

    results: list[dict[str, Any]] = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(_call_llm, client, prompt_def.system_prompt, row): row
            for _, row in df.iterrows()
        }
        done = 0
        for fut in as_completed(futures):
            r = fut.result()
            results.append(r)
            done += 1
            if progress_callback:
                try:
                    progress_callback(done, n)
                except Exception:
                    pass
    elapsed = time.time() - start

    rdf = pd.DataFrame(results)
    rdf = rdf.merge(
        df[["review_id", "rating", "gold_sentiment", "review_action", "ai_sentiment"]],
        on="review_id",
        how="left",
    )
    rdf["correct"] = rdf["sentiment"] == rdf["gold_sentiment"]

    tokens_in = int(rdf["tokens_in"].sum())
    tokens_out = int(rdf["tokens_out"].sum())
    cost = tokens_in * INPUT_PRICE_PER_M / 1e6 + tokens_out * OUTPUT_PRICE_PER_M / 1e6
    n_failures = int((~rdf["ok"]).sum())

    overall_acc = rdf["correct"].sum() / n if n else 0.0

    bad_ids = set(rdf[rdf["review_action"] == "reject"]["review_id"])
    bad_sub = rdf[rdf["review_id"].isin(bad_ids)]
    bad_acc = bad_sub["correct"].sum() / max(len(bad_sub), 1)

    high_sub = rdf[rdf["rating"] >= 4]
    high_acc = high_sub["correct"].sum() / max(len(high_sub), 1)

    mid_sub = rdf[rdf["rating"] == 3]
    mid_acc = mid_sub["correct"].sum() / max(len(mid_sub), 1)

    return EvalResult(
        prompt_version=prompt_version,
        golden_set_version=golden_set_version,
        n_samples=n,
        sentiment_accuracy=overall_acc,
        bad_case_accuracy=bad_acc,
        high_rating_accuracy=high_acc,
        mid_rating_accuracy=mid_acc,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_yuan=cost,
        elapsed_seconds=elapsed,
        raw_results=rdf,
        n_call_failures=n_failures,
    )
