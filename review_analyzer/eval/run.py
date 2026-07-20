"""评测 CLI — CI 入口.

# CI trigger: pet golden set v1.1 reviewed status support (2026-07-20)
用法:
    python3 -m review_analyzer.eval.run --prompt-version v2.1 --golden-set v1.0
    python3 -m review_analyzer.eval.run --prompt-version v2.1 --golden-set v1.1 --category pet
    python3 -m review_analyzer.eval.run --prompt-version v2.1 --baseline v1.0 --min-accuracy 0.92
    python3 -m review_analyzer.eval.run --prompt-version v2.1 --json-out result.json
    python3 -m review_analyzer.eval.run --prompt-version v2.3 --golden-set v1.1 --all-categories

退出码:
    0  评测通过（准确率不退化 + 达到 min-accuracy）
    1  评测失败：准确率低于 min-accuracy 或低于 baseline
    2  系统错误：DEEPSEEK_API_KEY 缺失 / 文件缺失 / 调用失败率过高
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import evaluate

ROOT = Path(__file__).resolve().parent.parent.parent


def _print_progress(done: int, total: int) -> None:
    if done % max(1, total // 10) == 0 or done == total:
        sys.stderr.write(f"\r  评测进度 {done}/{total}")
        sys.stderr.flush()
    if done == total:
        sys.stderr.write("\n")


def _discover_categories(golden_set_version: str) -> list[str]:
    """Discover all category subdirectories under a golden set version."""
    base = ROOT / "data" / "golden_set" / golden_set_version
    if not base.exists():
        return []
    categories = []
    for d in sorted(base.iterdir()):
        if d.is_dir() and list(d.glob("ai_annotated_*.csv")):
            categories.append(d.name)
    return categories


def _run_single(args: argparse.Namespace, category: str | None = None) -> int:
    """Run eval for a single golden set (optionally category-scoped)."""
    golden_set_version = args.golden_set
    label = f"golden_set={golden_set_version}"
    if category:
        label += f" category={category}"

    print(f"[eval] 评测 prompt={args.prompt_version} on {label}", file=sys.stderr)

    try:
        result = evaluate(
            prompt_version=args.prompt_version,
            golden_set_version=golden_set_version,
            category=category,
            max_workers=args.max_workers,
            progress_callback=_print_progress,
        )
    except FileNotFoundError as e:
        print(f"[eval] 跳过: {e}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"[eval] 系统错误: {e}", file=sys.stderr)
        return 2

    metrics = result.to_dict()
    print(f"\n[eval] 评测结果 ({label}):", file=sys.stderr)
    print(json.dumps(metrics, ensure_ascii=False, indent=2), file=sys.stderr)

    if args.json_out:
        suffix = f"_{category}" if category else ""
        out_path = args.json_out.replace(".json", f"{suffix}.json") if category else args.json_out
        Path(out_path).write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[eval] JSON 已写入 {out_path}", file=sys.stderr)

    if args.raw_out:
        suffix = f"_{category}" if category else ""
        raw_path = args.raw_out.replace(".csv", f"{suffix}.csv") if category else args.raw_out
        result.raw_results.to_csv(raw_path, index=False)

    failure_rate = result.n_call_failures / max(result.n_samples, 1)
    if failure_rate > args.max_failure_rate:
        print(
            f"[eval] ❌ LLM 调用失败率 {failure_rate:.1%} 超过上限 {args.max_failure_rate:.1%}",
            file=sys.stderr,
        )
        return 2

    if args.baseline:
        try:
            baseline_result = evaluate(
                prompt_version=args.baseline,
                golden_set_version=golden_set_version,
                category=category,
                max_workers=args.max_workers,
                progress_callback=_print_progress,
            )
        except Exception as e:
            print(f"[eval] 系统错误（评测 baseline {args.baseline}）: {e}", file=sys.stderr)
            return 2
        print(
            f"[eval] baseline {args.baseline} 准确率 {baseline_result.sentiment_accuracy:.1%}",
            file=sys.stderr,
        )
        if result.sentiment_accuracy < baseline_result.sentiment_accuracy:
            print(
                f"[eval] ❌ {args.prompt_version} 准确率 {result.sentiment_accuracy:.1%} "
                f"低于 baseline {args.baseline} {baseline_result.sentiment_accuracy:.1%}",
                file=sys.stderr,
            )
            return 1

    if result.sentiment_accuracy < args.min_accuracy:
        print(
            f"[eval] ❌ 准确率 {result.sentiment_accuracy:.1%} 低于 min-accuracy {args.min_accuracy:.1%}",
            file=sys.stderr,
        )
        return 1

    print(
        f"[eval] ✅ {args.prompt_version} 准确率 {result.sentiment_accuracy:.1%}（{result.n_samples} 条）",
        file=sys.stderr,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ClueAI Golden Set 评测 CLI")
    parser.add_argument("--prompt-version", default="v2.1",
                        help="要评测的 prompt 版本（默认 v2.1）")
    parser.add_argument("--golden-set", default="v1.0",
                        help="Golden Set 版本（默认 v1.0）")
    parser.add_argument("--category", default=None,
                        help="指定品类子目录（如 pet, 3c）；仅对 v1.1+ 有效")
    parser.add_argument("--all-categories", action="store_true",
                        help="遍历 golden set 下所有品类子目录逐一评测")
    parser.add_argument("--baseline", default=None,
                        help="对比基线 prompt 版本，evaluate 后准确率不能低于此版本")
    parser.add_argument("--min-accuracy", type=float, default=0.0,
                        help="最低准确率阈值（0-1，默认 0 不卡）")
    parser.add_argument("--max-failure-rate", type=float, default=0.05,
                        help="单次评测允许的 LLM 调用失败率上限（默认 5%%）")
    parser.add_argument("--json-out", default=None,
                        help="评测指标 JSON 输出路径（CI 用）")
    parser.add_argument("--raw-out", default=None,
                        help="评测明细 CSV 输出路径")
    parser.add_argument("--max-workers", type=int, default=8)
    args = parser.parse_args()

    if args.all_categories:
        categories = _discover_categories(args.golden_set)
        if not categories:
            print(f"[eval] 未找到 {args.golden_set} 下的品类子目录", file=sys.stderr)
            return 2
        print(f"[eval] 发现 {len(categories)} 个品类: {categories}", file=sys.stderr)
        worst_code = 0
        for cat in categories:
            code = _run_single(args, category=cat)
            worst_code = max(worst_code, code)
        return worst_code

    return _run_single(args, category=args.category)


if __name__ == "__main__":
    sys.exit(main())
