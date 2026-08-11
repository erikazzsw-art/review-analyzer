#!/usr/bin/env python3
"""5.9 阶段 A —— 六指标验收脚本.

跑生产同一条链路（deep_analyzer → enrich_aspects_json →
decorate_comment_customer_labels → iter_occurrences），输出六指标对比表。

Usage:
  # 首次运行（调 LLM，生成缓存）：
  python scripts/acceptance_six_metrics.py \
    --fixture backend_api/tests/fixtures/customer_label_waders_351_400_human_gold.json \
    --output-cache tmp/acceptance_waders_llm_cache.json

  # 后续运行 / CI（用缓存，不调 LLM）：
  python scripts/acceptance_six_metrics.py \
    --fixture backend_api/tests/fixtures/customer_label_waders_351_400_human_gold.json \
    --cached-llm tmp/acceptance_waders_llm_cache.json

  # 指定类目（默认 waders）：
  python scripts/acceptance_six_metrics.py --fixture <path> --category apparel
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 项目根
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# 生产链路函数（与 workers/jobs.py 同一条）
# ---------------------------------------------------------------------------
from backend_api.app.services.deep_analyzer import analyze_batch as deep_analyze_batch
from backend_api.app.services.specific_issue import (
    CUSTOMER_LABEL_OCCURRENCE_RULESET_VERSION,
    HIGHLIGHT_RULESET_VERSION,
    ISSUE_RULESET_VERSION,
    decorate_comment_customer_labels,
    enrich_aspects_json,
    iter_customer_highlight_occurrences,
    iter_specific_issue_occurrences,
)
from backend_api.app.services.taxonomy_loader import (
    get_fallback_aspects,
    render_aspects_block,
)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
PROMPT_VERSION = "v2.1"
ANALYZER_VERSION = "v4t3"
CACHE_MODEL_NAME = "gpt-4o-mini"  # 与 workers/jobs.py 的 CACHE_MODEL_NAME 一致

# 会被计算错误率（见基线文档第 6 节"停止规则"）
SERIAL_VIOLATION_CANONICAL: set[str] = {
    # 旧产品 / 竞品 / 替代品误标为当前产品问题/亮点
    "old_model_comparison",
    "competitor_comparison",
    "logistics_only",
    "not_current_product",
}

# ---------------------------------------------------------------------------
# 硬编码 waders taxonomy（CI 无 DB 时使用，与 DB 中 category_aspect_taxonomy 同步）
# 更新规则：每当生产 DB 的 waders taxonomy 变更时，同步更新此列表
# ---------------------------------------------------------------------------
_WADERS_TAXONOMY_FALLBACK: list[dict[str, str]] = [
    {"key": "accessory_storage", "label_zh": "口袋/配件收纳",
     "boundary_note": "胸前口袋、手机防水袋、修补贴、挂架、收纳和晾干配件是否好用或缺失"},
    {"key": "aesthetics", "label_zh": "外观设计",
     "boundary_note": "颜色、款式、儿童/成人穿着外观是否好看，不含尺码适配"},
    {"key": "boot_fit", "label_zh": "靴码/脚部适配",
     "boundary_note": "一体靴的鞋码、脚趾空间、脚踝/小腿松紧、是否需要大一码，不含鞋底抓地（归 grip）"},
    {"key": "breathability", "label_zh": "透气排湿",
     "boundary_note": "闷热、出汗、内部潮湿是否来自不透气；外部进水或漏水归 waterproof/seam_integrity"},
    {"key": "build_quality", "label_zh": "做工",
     "boundary_note": "肩带、腰带、扣具、车线、口袋等制造工艺细节；接缝漏水归 seam_integrity"},
    {"key": "comfort", "label_zh": "穿着舒适度",
     "boundary_note": "长时间涉水、行走或站立时的脚感、摩擦、压迫和疲劳感，不含尺码准确性（归 size_fit/boot_fit）"},
    {"key": "customer_service", "label_zh": "客服",
     "boundary_note": "售后响应、退款、换货、质保注册与卖家沟通体验"},
    {"key": "durability", "label_zh": "耐用性",
     "boundary_note": "多次使用、灌木/岩石/树枝摩擦后的抗撕裂、抗磨损和使用寿命；接缝专门问题归 seam_integrity"},
    {"key": "ease_of_use", "label_zh": "穿脱/调节便利",
     "boundary_note": "穿脱、肩带/腰带调节、清洗晾干是否方便；附带收纳挂架本身归 accessory_storage"},
    {"key": "grip", "label_zh": "鞋底抓地力",
     "boundary_note": "一体靴鞋底在河床、泥地、岩石、沙滩上的防滑和胎纹表现，不含靴码大小（归 boot_fit）"},
    {"key": "material", "label_zh": "材质用料",
     "boundary_note": "PVC/橡胶/尼龙/氯丁橡胶等材料厚薄、柔软度、气味和质感；实际破损寿命归 durability"},
    {"key": "mobility", "label_zh": "活动灵活性",
     "boundary_note": "穿着时走路、弯腰、下蹲、爬坡、儿童玩耍是否受限，不含单纯舒适脚感（归 comfort）"},
    {"key": "packaging", "label_zh": "包装",
     "boundary_note": "外包装、盒内摆放、开箱状态和包装保护，不含到货错发/已使用（归 shipping_damage）"},
    {"key": "seam_integrity", "label_zh": "接缝密封",
     "boundary_note": "腿部、裆部、靴子连接处等接缝是否开裂、渗水或脱胶，不含普通面料破洞（归 durability）"},
    {"key": "shipping_damage", "label_zh": "运输/到货问题",
     "boundary_note": "到货时错尺码、错颜色、已使用、脏污、运输损坏等履约问题，不含产品使用后损坏"},
    {"key": "size_fit", "label_zh": "整体尺码",
     "boundary_note": "胸围、腰围、裤长、裆部、儿童身高体重等整体尺码是否准确；仅鞋靴尺码归 boot_fit"},
    {"key": "temperature_rating", "label_zh": "保暖性",
     "boundary_note": "冷水、冬季、长时间站水中脚部或身体保暖表现；闷热出汗归 breathability"},
    {"key": "value_for_money", "label_zh": "性价比",
     "boundary_note": "价格与防水、耐用、配件和整体品质之间的匹配感"},
    {"key": "waterproof", "label_zh": "防水性",
     "boundary_note": "涉水裤整体是否进水、漏水或保持身体干燥；接缝/靴筒连接处明确漏水时归 seam_integrity"},
    {"key": "weight", "label_zh": "重量",
     "boundary_note": "涉水裤整体或靴子轻重、进水后是否沉重；收纳便利和附赠挂架归 accessory_storage"},
    {"key": "other", "label_zh": "其他", "boundary_note": ""},
]


# ===================================================================
# Helpers
# ===================================================================

def _review_from_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """将 fixture sample 转为 deep_analyzer 能用的 comment dict."""
    return {
        "id": sample.get("review_no") or sample.get("id"),
        "content": sample["content"],
        "rating": sample.get("rating") or 3,
        "title": "",
    }


def _gold_labels(sample: dict[str, Any]) -> dict[str, set[str]]:
    """提取 gold 标签（canonical keys）。"""
    return {
        "issue": set(sample.get("expected_issue_keys") or []),
        "highlight": set(sample.get("expected_highlight_keys") or []),
    }


def _system_keys_from_comment(comment: dict[str, Any], locale: str = "en") -> dict[str, set[str]]:
    """从一条已装饰的 comment 里提取系统输出的 canonical label keys。

    走生产同一读取链：iter_specific_issue_occurrences /
    iter_customer_highlight_occurrences。
    """
    issues: set[str] = set()
    for occ in iter_specific_issue_occurrences(comment, locale=locale):
        key = str(occ.get("canonical_label_key") or "").strip()
        if key:
            issues.add(key)

    highlights: set[str] = set()
    for occ in iter_customer_highlight_occurrences(comment, locale=locale):
        key = str(occ.get("canonical_label_key") or "").strip()
        if key:
            highlights.add(key)

    return {"issue": issues, "highlight": highlights}


def _other_counts_from_comment(comment: dict[str, Any]) -> dict[str, int]:
    """从一条已装饰的 comment 中读取 other 片段计数。

    依赖 enrich_aspects_json() 写入的 _other_fragment_count 和
    _total_fragment_count 字段。
    """
    aj = comment.get("aspects_json") or {}
    return {
        "other": aj.get("_other_fragment_count", 0),
        "total": aj.get("_total_fragment_count", 0),
    }


def _gold_module_routing(
    sample: dict[str, Any],
) -> dict[str, set[str]]:
    """从 fixture sample 提取 gold 模块流向映射: canonical_key → 期望模块集合."""
    routing: dict[str, set[str]] = {}
    for ann in sample.get("annotated_review_labels") or []:
        key = str(ann.get("canonical_key") or "").strip()
        if not key:
            continue
        modules = [str(m).strip() for m in (ann.get("module_routing") or [])]
        if key not in routing:
            routing[key] = set()
        routing[key].update(modules)
    return routing


def _module_flow_accuracy(
    samples: list[dict[str, Any]],
    system_outputs: list[dict[str, set[str]]],
) -> dict[str, Any]:
    """计算模块流向正确率。

    对每个 TP label（系统输出 ∩ gold），检查系统模块是否匹配 gold 模块：
    - 系统 issue → product_issue 模块
    - 系统 highlight → product_highlight 模块
    - gold audit_filter → 系统应将其放入 audit（不出现在 frontstage）
    正确率 = 正确路由数 / TP 总数
    """
    correct = 0
    total_tp = 0
    # audit_filter violations: gold says audit_filter but system outputs frontstage
    audit_violations: list[dict[str, Any]] = []
    # consumer_profile / purchase_motive / unmet_need: system doesn't produce these
    unmeasurable_modules: set[str] = set()

    for sample, sys_out in zip(samples, system_outputs):
        gold_routing = _gold_module_routing(sample)
        review_no = sample.get("review_no", sample.get("id"))

        # TP = system labels that are also in gold
        tp_issue = sys_out["issue"] & set(gold_routing.keys())
        tp_highlight = sys_out["highlight"] & set(gold_routing.keys())

        for key in tp_issue:
            total_tp += 1
            gold_mods = gold_routing[key]
            if "product_issue" in gold_mods:
                correct += 1
            elif gold_mods:
                unmeasurable_modules.update(gold_mods - {"product_issue", "product_highlight", "audit_filter"})

        for key in tp_highlight:
            total_tp += 1
            gold_mods = gold_routing[key]
            if "product_highlight" in gold_mods:
                correct += 1
            elif gold_mods:
                unmeasurable_modules.update(gold_mods - {"product_issue", "product_highlight", "audit_filter"})

        # Check audit_filter violations: gold says audit_filter but system outputs
        for key in sys_out["issue"] | sys_out["highlight"]:
            gold_mods = gold_routing.get(key, set())
            if "audit_filter" in gold_mods:
                audit_violations.append({
                    "review_no": review_no,
                    "canonical_key": key,
                    "gold_modules": sorted(gold_mods),
                    "content_preview": sample["content"][:80],
                })

    rate = (correct / total_tp * 100) if total_tp > 0 else None
    return {
        "rate": round(rate, 1) if rate is not None else None,
        "correct": correct,
        "total_tp": total_tp,
        "audit_filter_violations": audit_violations,
        "unmeasurable_modules": sorted(unmeasurable_modules) if unmeasurable_modules else [],
        "formula": f"正确路由={correct} / TP总数={total_tp}" if total_tp > 0 else "N/A",
    }


def _polarity_flip_detail(
    samples: list[dict[str, Any]],
    system_outputs: list[dict[str, set[str]]],
) -> list[dict[str, Any]]:
    """极性反标明细（修正定义）：差评(≤2)拿到 highlight 或好评(≥4)拿到 issue，
    且 gold 没标同类型 label 的才算反标。

    返回每条反标的明细列表。
    """
    flips: list[dict[str, Any]] = []
    for sample, sys_out in zip(samples, system_outputs):
        rating = int(sample.get("rating") or 3)
        gold = _gold_labels(sample)
        review_no = sample.get("review_no", sample.get("id"))

        if rating <= 2 and sys_out["highlight"]:
            # 差评拿到 highlight → 只有 gold 没标 highlight 的才算
            unapproved = sys_out["highlight"] - gold["highlight"]
            if unapproved:
                flips.append({
                    "review_no": review_no,
                    "rating": rating,
                    "type": "差评(≤2)出highlight",
                    "content_preview": sample["content"][:120],
                    "flip_labels": sorted(unapproved),
                    "gold_also_highlight": sorted(sys_out["highlight"] & gold["highlight"]),
                    "all_sys_highlight": sorted(sys_out["highlight"]),
                })
        elif rating >= 4 and sys_out["issue"]:
            # 好评拿到 issue → 只有 gold 没标 issue 的才算
            unapproved = sys_out["issue"] - gold["issue"]
            if unapproved:
                flips.append({
                    "review_no": review_no,
                    "rating": rating,
                    "type": "好评(≥4)出issue",
                    "content_preview": sample["content"][:120],
                    "flip_labels": sorted(unapproved),
                    "gold_also_issue": sorted(sys_out["issue"] & gold["issue"]),
                    "all_sys_issue": sorted(sys_out["issue"]),
                })
    return flips


def _polarity_flip_count(
    samples: list[dict[str, Any]],
    system_outputs: list[dict[str, set[str]]],
) -> int:
    """数极性反标条数（修正定义）。

    差评(≤2)拿到 gold 没标的 highlight，或好评(≥4)拿到 gold 没标的 issue。
    中评(3)不参与极性判定。
    """
    return len(_polarity_flip_detail(samples, system_outputs))


def _serial_violation_count(
    samples: list[dict[str, Any]],
    system_outputs: list[dict[str, set[str]]],
    serial_keys: set[str],
) -> int:
    """数串台：已知串台类 canonical key 出现在系统输出里的条数."""
    count = 0
    for sample, sys_out in zip(samples, system_outputs):
        all_keys = sys_out["issue"] | sys_out["highlight"]
        if all_keys & serial_keys:
            count += 1
    return count


# ===================================================================
# Core: run production chain
# ===================================================================

def run_llm(
    samples: list[dict[str, Any]],
    *,
    sub_category: str = "waders",
    locale: str = "en",
) -> list[dict[str, Any]]:
    """调 deep_analyzer 跑 LLM，返回 raw aspects 列表。

    每条结果包含: aspects, sentiment, pain_points, highlights,
    model_used, tokens_in, tokens_out 等。
    """
    comments = [_review_from_sample(s) for s in samples]

    # 尝试从 DB 加载类目专属 taxonomy（同 workers/jobs.py 的 _resolve_job_taxonomy）
    # 若 DB 不可用（CI / 本地无 DB），使用硬编码 fallback
    from backend_api.app.services.taxonomy_loader import resolve_aspects

    taxonomy_aspects, taxonomy_hit = resolve_aspects(sub_category)
    if not taxonomy_hit:
        # DB 无此 sub_category → 检查是否有硬编码 fallback
        if sub_category == "waders":
            logger.info("Taxonomy not in DB for %s, using hardcoded waders fallback", sub_category)
            taxonomy_aspects = _WADERS_TAXONOMY_FALLBACK
        else:
            logger.info("Taxonomy not found for %s, using generic fallback aspects", sub_category)
            taxonomy_aspects = get_fallback_aspects()

    aspects_block = render_aspects_block(taxonomy_aspects)
    # 与 production 一致：allowed_aspects 必须是 taxonomy 中实际存在的 key 列表
    # production 代码（workers/jobs.py:527）：allowed_aspects = [a["key"] for a in aspects]
    # 传 None 会回退到硬编码 ASPECT_KEYS（21个通用key），其中不包含
    # waterproof/breathability/grip/mobility/seam_integrity 等 waders 专属 key，
    # 导致 LLM 按 waders prompt 输出却被 ASPECT_KEYS 拒绝 → 与生产行为不一致
    allowed_aspects: list[str] | None = [a["key"] for a in taxonomy_aspects]

    logger.info(
        "Running deep_analyze_batch on %d reviews, sub_category=%s, taxonomy_hit=%s, cost ~$0.003",
        len(comments),
        sub_category,
        taxonomy_hit,
    )
    results = deep_analyze_batch(
        comments=comments,
        sub_category=sub_category,
        prompt_version=PROMPT_VERSION,
        aspects_block=aspects_block,
        allowed_aspects=allowed_aspects,
        progress_callback=None,
        user_id=None,  # 不跟踪成本到 DB
        locale=locale,
        trace_callback=None,
    )
    logger.info("LLM complete: %d results", len(results))
    return results


def run_production_chain(
    sample: dict[str, Any],
    llm_result: dict[str, Any],
    *,
    sub_category: str = "waders",
    locale: str = "en",
) -> dict[str, Any]:
    """对一条评论跑完整生产后处理链路。

    1. 构建 aspects_json（同 workers/jobs.py）
    2. enrich_aspects_json → customer_label_occurrences
    3. decorate_comment_customer_labels → V2 frontstage + tags
    返回: 装饰后的 comment dict
    """
    comment = _review_from_sample(sample)

    if llm_result.get("error"):
        # LLM 失败 → 返回空标签 comment
        return {
            **comment,
            "aspects_json": {
                "sub_category": sub_category,
                "aspects": [],
                "customer_label_occurrences": [],
                "cluster_propagated": False,
                "analysis_error": llm_result.get("error", "unknown"),
            },
        }

    # 构建 aspects_json（与 workers/jobs.py 行 986-997 同构）
    aspects_json: dict[str, Any] = {
        "sentiment": llm_result.get("sentiment"),
        "aspects": llm_result.get("aspects", []),
        "pain_points": llm_result.get("pain_points", []),
        "highlights": llm_result.get("highlights", []),
        "evidence_level_overall": llm_result.get("evidence_level_overall"),
        "prompt_version": llm_result.get("prompt_version", PROMPT_VERSION),
        "cluster_propagated": llm_result.get("cluster_propagated", False),
        "model_name": llm_result.get("model_used", CACHE_MODEL_NAME),
        "sub_category": sub_category,
    }

    # enrich: aspects → customer_label_occurrences（同 workers/jobs.py 行 999-1004）
    enriched = enrich_aspects_json(
        aspects_json,
        sub_category=sub_category,
        content=comment.get("content", ""),
        locale=locale,
        comment_id=comment.get("id"),
    )

    if enriched:
        aspects_json = enriched

    comment["aspects_json"] = aspects_json

    # decorate: V2 frontstage + customer_issue_tags / customer_highlight_tags
    comment = decorate_comment_customer_labels(
        comment,
        locale=locale,
    )

    return comment


# ===================================================================
# Metrics calculation
# ===================================================================

def calculate_metrics(
    samples: list[dict[str, Any]],
    system_outputs: list[dict[str, set[str]]],
    decorated_comments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """从 gold vs system 计算六指标."""

    # --- 错标率：系统输出的标签中 gold 里没有的比例 ---
    total_system = 0
    total_fp = 0
    for sample, sys_out in zip(samples, system_outputs):
        gold = _gold_labels(sample)
        total_system += len(sys_out["issue"]) + len(sys_out["highlight"])
        total_fp += len(sys_out["issue"] - gold["issue"])
        total_fp += len(sys_out["highlight"] - gold["highlight"])
    false_positive_rate = (total_fp / total_system * 100) if total_system > 0 else 0.0

    # --- 漏标率：gold 标注中系统没输出的比例 ---
    total_gold = 0
    total_fn = 0
    for sample, sys_out in zip(samples, system_outputs):
        gold = _gold_labels(sample)
        total_gold += len(gold["issue"]) + len(gold["highlight"])
        total_fn += len(gold["issue"] - sys_out["issue"])
        total_fn += len(gold["highlight"] - sys_out["highlight"])
    false_negative_rate = (total_fn / total_gold * 100) if total_gold > 0 else 0.0

    # --- 极性反标数（修正定义：gold 没标 + 系统标了反极性 才算） ---
    polarity_flips = _polarity_flip_count(samples, system_outputs)
    polarity_flip_details = _polarity_flip_detail(samples, system_outputs)

    # --- 串台数 ---
    serial_violations = _serial_violation_count(
        samples, system_outputs, SERIAL_VIOLATION_CANONICAL
    )

    # --- 模块流向正确率 ---
    module_flow = _module_flow_accuracy(samples, system_outputs)
    module_flow_rate = module_flow["rate"]
    module_flow_note = module_flow["formula"]
    if module_flow["audit_filter_violations"]:
        av_count = len(module_flow["audit_filter_violations"])
        module_flow_note += f"（audit_filter违规={av_count}）"
    if module_flow["unmeasurable_modules"]:
        module_flow_note += f"；无法测量模块：{', '.join(module_flow['unmeasurable_modules'])}"

    # --- other 占比 ---
    other_rate: float | None = None
    other_note = ""
    if decorated_comments is not None:
        _total_other = 0
        _total_fragments = 0
        for c in decorated_comments:
            counts = _other_counts_from_comment(c)
            _total_other += counts["other"]
            _total_fragments += counts["total"]
        if _total_fragments > 0:
            other_rate = round(_total_other / _total_fragments * 100, 1)
            other_note = f"other片段={_total_other} / 总片段={_total_fragments}"
        else:
            other_note = "总片段数为 0，无法计算占比"
    else:
        other_note = "无法直接测量：当前链路不显式输出 other 片段占比。建议后续加 _other_fragment_count 字段"

    return {
        "false_positive_rate": round(false_positive_rate, 2),
        "false_positive_formula": f"FP={total_fp} / 系统输出总数={total_system}",
        "false_negative_rate": round(false_negative_rate, 2),
        "false_negative_formula": f"FN={total_fn} / gold总数={total_gold}",
        "polarity_flips": polarity_flips,
        "polarity_flip_details": polarity_flip_details,
        "serial_violations": serial_violations,
        "serial_keys_checked": sorted(SERIAL_VIOLATION_CANONICAL),
        "module_flow_rate": module_flow_rate,
        "module_flow_note": module_flow_note,
        "module_flow_correct": module_flow["correct"],
        "module_flow_total_tp": module_flow["total_tp"],
        "module_flow_audit_violations": module_flow["audit_filter_violations"],
        "module_flow_unmeasurable_modules": module_flow["unmeasurable_modules"],
        "other_rate": other_rate,
        "other_note": other_note,
        "total_system": total_system,
        "total_gold": total_gold,
        "total_fp": total_fp,
        "total_fn": total_fn,
    }


def per_sample_detail(
    samples: list[dict[str, Any]],
    system_outputs: list[dict[str, set[str]]],
    polarity_flip_details: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """逐条明细，方便 Erika 对照."""
    flip_reviews: dict[int, list[str]] = {}
    if polarity_flip_details:
        for f in polarity_flip_details:
            rn = f.get("review_no")
            if rn is not None:
                flip_reviews.setdefault(rn, []).extend(f.get("flip_labels", []))

    rows: list[dict[str, Any]] = []
    for i, (sample, sys_out) in enumerate(zip(samples, system_outputs)):
        gold = _gold_labels(sample)
        rn = sample.get("review_no", sample.get("id"))
        issue_fp = sorted(sys_out["issue"] - gold["issue"])
        issue_fn = sorted(gold["issue"] - sys_out["issue"])
        issue_tp = sorted(sys_out["issue"] & gold["issue"])
        hl_fp = sorted(sys_out["highlight"] - gold["highlight"])
        hl_fn = sorted(gold["highlight"] - sys_out["highlight"])
        hl_tp = sorted(sys_out["highlight"] & gold["highlight"])
        rows.append({
            "index": i,
            "review_no": rn,
            "content_preview": sample["content"][:100],
            "rating": sample.get("rating"),
            "issue_tp": issue_tp,
            "issue_fp": issue_fp,
            "issue_fn": issue_fn,
            "highlight_tp": hl_tp,
            "highlight_fp": hl_fp,
            "highlight_fn": hl_fn,
            "polarity_flip_labels": flip_reviews.get(rn, []),
        })
    return rows


# ===================================================================
# Output formatting
# ===================================================================

def print_report(
    metrics: dict[str, Any],
    details: list[dict[str, Any]],
    *,
    fixture_path: str,
    category: str,
    cache_used: bool,
) -> None:
    """输出 Markdown 格式的验收报告到 stdout."""
    print()
    print("=" * 70)
    print("  5.9 阶段 A —— 六指标验收报告")
    print("=" * 70)
    print()
    print(f"- 基准集：{fixture_path}")
    print(f"- 类目：{category}")
    print(f"- 评论数：{len(details)}")
    print(f"- 数据来源：{'缓存LLM结果' if cache_used else '实时LLM调用'}")
    print(f"- 生成时间：{datetime.now(timezone.utc).isoformat()}")
    print()

    # 六指标表
    print("## 六指标")
    print()
    print("| 指标 | 当前值 | 通过线 | 是否过线 | 算法说明 |")
    print("|------|--------|--------|----------|----------|")

    fp_rate = metrics["false_positive_rate"]
    fp_pass = "✅" if fp_rate <= 5.0 else "❌"
    print(f"| 错标率 | {fp_rate:.1f}% | ≤ 5% | {fp_pass} | {metrics['false_positive_formula']} |")

    fn_rate = metrics["false_negative_rate"]
    fn_pass = "✅" if fn_rate <= 20.0 else "❌"
    print(f"| 漏标率 | {fn_rate:.1f}% | ≤ 20% | {fn_pass} | {metrics['false_negative_formula']} |")

    pf = metrics["polarity_flips"]
    pf_pass = "✅" if pf == 0 else "❌ 红线"
    print(f"| 极性反标数 | {pf} | 必须 = 0 | {pf_pass} | 差评(≤2)标highlight或好评(≥4)标issue，且gold没标同类型label 的条数（修正定义） |")

    sv = metrics["serial_violations"]
    sv_pass = "✅" if sv == 0 else "❌ 红线"
    print(f"| 串台数 | {sv} | 必须 = 0 | {sv_pass} | 已知串台label出现在系统输出中的条数（{', '.join(metrics['serial_keys_checked'])}） |")

    mfr = metrics["module_flow_rate"]
    mf_pass = "✅" if (mfr is not None and mfr >= 90.0) else ("❌" if mfr is not None else "⚠️")
    print(f"| 模块流向正确率 | {"—" if mfr is None else f'{mfr:.1f}%'} | ≥ 90% | {mf_pass} | {metrics['module_flow_note']} |")

    oth = metrics["other_rate"]
    oth_pass = "✅" if (oth is not None and oth <= 15.0) else ("❌" if oth is not None else "⚠️ 无法测量")
    print(f"| other 占比 | {"—" if oth is None else f'{oth:.1f}%'} | ≤ 15% | {oth_pass} | {metrics['other_note']} |")

    print()
    print(f"**汇总**：系统输出标签 {metrics['total_system']} 个，gold 标签 {metrics['total_gold']} 个")
    print(f"FP={metrics['total_fp']}, FN={metrics['total_fn']}")

    # 极性反标明细
    flip_details = metrics.get("polarity_flip_details", [])
    if flip_details:
        print()
        print("## 极性反标明细（修正定义：gold没标+系统标了反极性 才算）")
        print()
        print("| review_no | rating | 类型 | 反标label | gold也标了（不算反标） | 内容片段 |")
        print("|-----------|--------|------|-----------|----------------------|----------|")
        for f in flip_details:
            gold_ok = f.get("gold_also_highlight", []) or f.get("gold_also_issue", [])
            content = f["content_preview"][:80]
            print(f"| #{f['review_no']} | {f['rating']} | {f['type']} | {', '.join(f['flip_labels'])} | {', '.join(gold_ok) if gold_ok else '—'} | {content}... |")
        print()

    # 模块流向：audit_filter 违规明细
    audit_violations = metrics.get("module_flow_audit_violations", [])
    if audit_violations:
        print()
        print("## 模块流向：audit_filter 违规明细（gold标audit_filter但系统输出到了frontstage）")
        print()
        print("| review_no | canonical_key | gold_modules | 内容片段 |")
        print("|-----------|---------------|-------------|----------|")
        for av in audit_violations:
            content = av["content_preview"][:80]
            print(f"| #{av['review_no']} | {av['canonical_key']} | {', '.join(av['gold_modules'])} | {content}... |")
        print()

    # 逐条明细
    print()
    print("## 逐条明细")
    print()
    for row in details:
        print(f"### [{row['index']+1}] review #{row['review_no']} (rating={row['rating']})")
        print(f"> {row['content_preview']}...")
        print()
        if row["polarity_flip_labels"]:
            print(f"- 🔴 极性反标: {', '.join(row['polarity_flip_labels'])}")
        if row["issue_tp"]:
            print(f"- issue ✅: {', '.join(row['issue_tp'])}")
        if row["issue_fp"]:
            print(f"- issue ❌ (错标): {', '.join(row['issue_fp'])}")
        if row["issue_fn"]:
            print(f"- issue ⚠️ (漏标): {', '.join(row['issue_fn'])}")
        if row["highlight_tp"]:
            print(f"- highlight ✅: {', '.join(row['highlight_tp'])}")
        if row["highlight_fp"]:
            print(f"- highlight ❌ (错标): {', '.join(row['highlight_fp'])}")
        if row["highlight_fn"]:
            print(f"- highlight ⚠️ (漏标): {', '.join(row['highlight_fn'])}")
        if not any([row["issue_tp"], row["issue_fp"], row["issue_fn"],
                     row["highlight_tp"], row["highlight_fp"], row["highlight_fn"]]):
            print("- （无标签）")
        print()

    # 缺口说明
    print("## 缺口说明")
    print()
    print("以下指标本次**无法测量**：")
    print()
    print(f"- **模块流向正确率**：{metrics['module_flow_note']}")
    print(f"- **other 占比**：{metrics['other_note']}")
    print()

    # 红线状态
    red_lines_broken = []
    if metrics["polarity_flips"] > 0:
        red_lines_broken.append(f"极性反标={metrics['polarity_flips']}")
    if metrics["serial_violations"] > 0:
        red_lines_broken.append(f"串台={metrics['serial_violations']}")

    if red_lines_broken:
        print(f"❌ **红线已破**：{', '.join(red_lines_broken)}")
    else:
        print("✅ 红线（极性反标、串台）未破")

    print()

    # JSON 输出（方便 CI 解析）
    json_output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fixture": str(fixture_path),
        "category": category,
        "review_count": len(details),
        "cache_used": cache_used,
        "metrics": metrics,
        "red_lines_broken": red_lines_broken,
        "exit_code": 0 if not red_lines_broken else 1,
    }
    print("## JSON (CI)")
    print()
    print("```json")
    print(json.dumps(json_output, ensure_ascii=False, indent=2))
    print("```")


# ===================================================================
# Main
# ===================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="5.9 阶段 A 六指标验收脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--fixture",
        required=True,
        help="Path to human gold fixture JSON",
    )
    parser.add_argument(
        "--category",
        default="waders",
        help="Sub-category for analysis (default: waders)",
    )
    parser.add_argument(
        "--cached-llm",
        default=None,
        help="Path to cached raw LLM aspects JSON (skip LLM call)",
    )
    parser.add_argument(
        "--output-cache",
        default=None,
        help="Save raw LLM results to this path for CI reuse",
    )
    parser.add_argument(
        "--locale",
        default="en",
        help="Locale for analysis (default: en)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    fixture_path = Path(args.fixture)
    if not fixture_path.exists():
        print(f"ERROR: fixture not found: {fixture_path}", file=sys.stderr)
        return 2

    # ------------------------------------------------------------------
    # 1. 加载 fixture
    # ------------------------------------------------------------------
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    samples: list[dict[str, Any]] = fixture.get("samples") or []
    if not samples:
        print("ERROR: fixture has no 'samples'", file=sys.stderr)
        return 2

    logger.info("Loaded %d samples from %s", len(samples), fixture_path)

    # ------------------------------------------------------------------
    # 2. 获取 raw LLM aspects（从缓存或实时调用）
    # ------------------------------------------------------------------
    cache_used = False
    if args.cached_llm:
        cache_path = Path(args.cached_llm)
        if not cache_path.exists():
            print(f"ERROR: cache file not found: {cache_path}", file=sys.stderr)
            return 2
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        llm_results = cached["results"]
        logger.info("Loaded %d cached LLM results from %s", len(llm_results), cache_path)
        cache_used = True
    else:
        # 实时调 LLM
        llm_results = run_llm(samples, sub_category=args.category, locale=args.locale)

        if args.output_cache:
            cache_path = Path(args.output_cache)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {
                "fixture": str(fixture_path),
                "category": args.category,
                "prompt_version": PROMPT_VERSION,
                "review_count": len(samples),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "results": llm_results,
            }
            cache_path.write_text(
                json.dumps(cache_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Saved LLM cache to %s", cache_path)

    if len(llm_results) != len(samples):
        logger.warning(
            "LLM results count mismatch: %d vs %d samples",
            len(llm_results),
            len(samples),
        )

    # ------------------------------------------------------------------
    # 3. 跑生产后处理链路 + 提取系统输出
    # ------------------------------------------------------------------
    decorated_comments: list[dict[str, Any]] = []
    system_outputs: list[dict[str, set[str]]] = []

    for sample, llm_result in zip(samples, llm_results):
        comment = run_production_chain(
            sample,
            llm_result,
            sub_category=args.category,
            locale=args.locale,
        )
        decorated_comments.append(comment)
        sys_keys = _system_keys_from_comment(comment, locale=args.locale)
        system_outputs.append(sys_keys)

    # ------------------------------------------------------------------
    # 4. 计算指标
    # ------------------------------------------------------------------
    metrics = calculate_metrics(samples, system_outputs, decorated_comments)
    details = per_sample_detail(samples, system_outputs, metrics.get("polarity_flip_details"))
    print_report(
        metrics,
        details,
        fixture_path=str(fixture_path),
        category=args.category,
        cache_used=cache_used,
    )

    # 红线破了 → exit 1
    if metrics["polarity_flips"] > 0 or metrics["serial_violations"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
