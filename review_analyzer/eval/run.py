"""评测 CLI — CI 入口.

用法:
    python3 -m review_analyzer.eval.run --prompt-version v2.1 --golden-set v1.0
    python3 -m review_analyzer.eval.run --prompt-version v2.1 --baseline v1.0 --min-accuracy 0.92
    python3 -m review_analyzer.eval.run --prompt-version v2.1 --json-out result.json

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


def _print_progress(done: int, total: int) -> None:
    if done % max(1, total // 10) == 0 or done == total:
        sys.stderr.write(f"\r  评测进度 {done}/{total}")
        sys.stderr.flush()
    if done == total:
        sys.stderr.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="ClueAI Golden Set 评测 CLI")
    parser.add_argument("--prompt-version", default="v2.1",
                        help="要评测的 prompt 版本（默认 v2.1）")
    parser.add_argument("--golden-set", default="v1.0",
                        help="Golden Set 版本（默认 v1.0）")
    parser.add_argument("--baseline", default=None,
                        help="对比基线 prompt 版本，evaluate 后准确率不能低于此版本")
    parser.add_argument("--min-accuracy", type=float, default=0.0,
                        help="最低准确率阈值（0-1，默认 0 不卡）")
    parser.add_argument("--max-failure-rate", type=float, default=0.05,
                        help="单次评测允许的 LLM 调用失败率上限（默认 5%%）")
    parser.add_argument("--json-out", default=None,
                        help="评测指标 JSON 输出路径（CI 用）")
    parser.add_argument("--raw-out", default=None,
                        help="评测明细 CSV 输出路径（包含每条 review 的预测/真值/是否正确）")
    parser.add_argument("--max-workers", type=int, default=8)
    args = parser.parse_args()

    print(f"[eval] 评测 prompt={args.prompt_version} on golden_set={args.golden_set}",
          file=sys.stderr)

    try:
        result = evaluate(
            prompt_version=args.prompt_version,
            golden_set_version=args.golden_set,
            max_workers=args.max_workers,
            progress_callback=_print_progress,
        )
    except Exception as e:
        print(f"[eval] 系统错误: {e}", file=sys.stderr)
        return 2

    metrics = result.to_dict()
    print("\n[eval] 评测结果:", file=sys.stderr)
    print(json.dumps(metrics, ensure_ascii=False, indent=2), file=sys.stderr)

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[eval] JSON 已写入 {args.json_out}", file=sys.stderr)

    if args.raw_out:
        result.raw_results.to_csv(args.raw_out, index=False)
        print(f"[eval] 明细 CSV 已写入 {args.raw_out}（{len(result.raw_results)} 行）",
              file=sys.stderr)

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
                golden_set_version=args.golden_set,
                max_workers=args.max_workers,
                progress_callback=_print_progress,
            )
        except Exception as e:
            print(f"[eval] 系统错误（评测 baseline {args.baseline}）: {e}",
                  file=sys.stderr)
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


if __name__ == "__main__":
    sys.exit(main())
