#!/usr/bin/env python3
"""并发分析性能测试

对比串行 vs 并发分析的耗时差异。
测试 10 条评论的真实 API 调用时间，推算 100 条的预期耗时。
"""

import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "review_analyzer", ".env"))

from review_analyzer.analyzer import analyze_comment, analyze_batch, _make_unrecognizable

API_KEY = os.getenv("DEEPSEEK_API_KEY")

test_reviews = [
    {"content": "This desk is very sturdy and looks great in my home office. Easy to assemble too!", "rating": 5},
    {"content": "The chair arrived with a broken leg. Very disappointed with the quality.", "rating": 1},
    {"content": "Decent table for the price. Nothing special but gets the job done.", "rating": 3},
    {"content": "Absolutely love this bookshelf! Perfect size and the wood quality is excellent.", "rating": 5},
    {"content": "Terrible experience. The drawer doesn't close properly and the finish is chipping.", "rating": 1},
    {"content": "Good value for money. Assembly was a bit tricky but the end result looks nice.", "rating": 4},
    {"content": "The mattress is too soft and sags in the middle after just one month of use.", "rating": 2},
    {"content": "Beautiful dining set! Received many compliments from guests. Highly recommend.", "rating": 5},
    {"content": "The color is nothing like the picture. Also the material feels cheap and flimsy.", "rating": 2},
    {"content": "Solid construction and fast delivery. Would buy from this brand again.", "rating": 4},
]


def test_serial(reviews: list[dict]) -> tuple[float, list[dict]]:
    """串行测试"""
    print(f"\n=== 串行分析 {len(reviews)} 条评论 ===")
    results = []
    total = len(reviews)
    start = time.time()

    for i, item in enumerate(reviews):
        content = item.get("content", "").strip()
        rating = item.get("rating")
        try:
            analysis = analyze_comment(content, "家具家居", API_KEY, rating)
        except Exception as e:
            print(f"  第 {i+1} 条失败: {e}")
            analysis = _make_unrecognizable()
        results.append({**item, **analysis})
        print(f"  [{i+1}/{total}] 完成")

    elapsed = time.time() - start
    success = sum(1 for r in results if r.get("sentiment") != "unrecognizable")
    print(f"耗时: {elapsed:.1f}s | 成功: {success}/{total} | 每条平均: {elapsed/total:.2f}s")
    print(f"推算 100 条: {elapsed/total*100:.0f}s")
    return elapsed, results


def test_concurrent(reviews: list[dict], max_workers: int = 10) -> tuple[float, list[dict]]:
    """并发测试"""
    print(f"\n=== 并发分析 {len(reviews)} 条评论 (workers={max_workers}) ===")
    progress_lock = threading.Lock()

    def progress_cb(current, total):
        with progress_lock:
            print(f"  [{current}/{total}] 完成")

    start = time.time()
    results = analyze_batch(reviews, category="家具家居", api_key=API_KEY, progress_callback=progress_cb, max_workers=max_workers)
    elapsed = time.time() - start

    success = sum(1 for r in results if r and r.get("sentiment") != "unrecognizable")
    print(f"耗时: {elapsed:.1f}s | 成功: {success}/{len(reviews)} | 每条平均: {elapsed/len(reviews):.2f}s")
    print(f"推算 100 条: {elapsed/len(reviews)*100:.0f}s")
    return elapsed, results


if __name__ == "__main__":
    if not API_KEY:
        print("错误：未找到 DEEPSEEK_API_KEY 环境变量")
        sys.exit(1)

    print("=" * 60)
    print("并发分析性能对比测试")
    print("=" * 60)

    serial_time, serial_results = test_serial(test_reviews)
    concurrent_time, concurrent_results = test_concurrent(test_reviews, max_workers=10)

    print("\n" + "=" * 60)
    print("对比结果")
    print("=" * 60)
    speedup = serial_time / concurrent_time if concurrent_time > 0 else 0
    print(f"串行耗时:   {serial_time:.1f}s  (推算100条: {serial_time/10*100:.0f}s)")
    print(f"并发耗时:   {concurrent_time:.1f}s  (推算100条: {concurrent_time/10*100:.0f}s)")
    print(f"加速比:     {speedup:.1f}x")

    projected_100 = concurrent_time / 10 * 100
    if projected_100 <= 60:
        print(f"\n✅ 100 条推算耗时 {projected_100:.0f}s ≤ 60s，达标！")
    else:
        print(f"\n⚠️ 100 条推算耗时 {projected_100:.0f}s > 60s，需进一步优化")

    print("\n--- 并发结果抽样 ---")
    for r in concurrent_results[:3]:
        if r:
            print(f"  [{r.get('sentiment')}] {r.get('summary', 'N/A')} | tags: {r.get('issue_tag', r.get('highlight_tag', 'N/A'))}")
