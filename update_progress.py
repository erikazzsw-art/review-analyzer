#!/usr/bin/env python3
"""
自动更新 PROGRESS.md 的脚本。
读取 PROGRESS.md 中的 checkbox 状态，计算各模块和总体进度，原地更新文件。
可通过 Git post-commit hook 自动调用。
"""
import re
import math
from pathlib import Path
from datetime import datetime

PROGRESS_FILE = Path(__file__).parent / "PROGRESS.md"

def parse_and_update():
    text = PROGRESS_FILE.read_text(encoding="utf-8")

    module_pattern = re.compile(
        r"### (M\d+): .+?\n"
        r"(.*?)"
        r"(?=\n### M\d+:|\n---|\Z)",
        re.DOTALL,
    )

    total_tasks = 0
    done_tasks = 0
    module_stats: list[tuple[str, int, int]] = []

    for m in module_pattern.finditer(text):
        mid = m.group(1)
        block = m.group(2)
        checked = len(re.findall(r"- \[x\]", block))
        unchecked = len(re.findall(r"- \[ \]", block))
        t = checked + unchecked
        module_stats.append((mid, checked, t))
        total_tasks += t
        done_tasks += checked

    total_modules = len(module_stats)
    done_modules = sum(1 for _, d, t in module_stats if t > 0 and d == t)
    in_progress = sum(1 for _, d, t in module_stats if 0 < d < t)
    not_started = total_modules - done_modules - in_progress
    pct = math.floor(done_tasks / total_tasks * 100) if total_tasks else 0

    filled = pct // 5
    bar = "█" * filled + "░" * (20 - filled)

    text = re.sub(
        r"(总模块数 \| )\d+", rf"\g<1>{total_modules}", text
    )
    text = re.sub(
        r"(已完成 \| )\d+", rf"\g<1>{done_modules}", text
    )
    text = re.sub(
        r"(进行中 \| )\d+", rf"\g<1>{in_progress}", text
    )
    text = re.sub(
        r"(未开始 \| )\d+", rf"\g<1>{not_started}", text
    )
    text = re.sub(
        r"(总体进度 \| )\d+%", rf"\g<1>{pct}%", text
    )
    text = re.sub(
        r"\[.{20}\] \d+%",
        f"[{bar}] {pct}%",
        text,
    )

    for mid, d, t in module_stats:
        mpct = math.floor(d / t * 100) if t else 0
        if d == t and t > 0:
            status = "已完成"
        elif d > 0:
            status = "进行中"
        else:
            status = "未开始"
        text = re.sub(
            rf"(### {mid}: .+?\n- .+?状态: ).+?( \| 进度: )\d+%",
            rf"\g<1>{status}\g<2>{mpct}%",
            text,
        )

    today = datetime.now().strftime("%Y-%m-%d")
    text = re.sub(
        r"(> 最后更新：)\S+",
        rf"\g<1>{today}",
        text,
    )

    PROGRESS_FILE.write_text(text, encoding="utf-8")
    print(f"PROGRESS.md updated: {pct}% ({done_tasks}/{total_tasks} tasks)")

if __name__ == "__main__":
    parse_and_update()
