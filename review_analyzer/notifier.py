"""飞书推送 — Webhook 通知 + 推送规则引擎"""

import base64
import hashlib
import hmac
import json
import logging
import time
from collections import Counter
from datetime import datetime, timedelta

import requests

from .database import get_comments, get_session_by_id, get_sessions, get_setting

logger = logging.getLogger(__name__)

FEISHU_TIMEOUT = 10


def _format_notification_text(
    session_data: dict,
    top_issues: list[dict],
    high_priority_count: int,
) -> str:
    """格式化推送文本（纯文本，适用于飞书富文本消息体）"""
    product_id = session_data.get("product_id", "")
    total = session_data.get("total_reviews", 0)
    neg_count = session_data.get("negative_count", 0)
    neg_rate = neg_count / total * 100 if total > 0 else 0

    lines = [
        f"📊 评论分析完成 | {product_id}",
        "",
        f"本次分析：{total} 条 | 差评率：{neg_rate:.1f}%",
        "",
    ]

    if top_issues:
        lines.append("TOP3 核心问题：")
        for i, issue in enumerate(top_issues[:3], 1):
            count = issue.get("count", 0)
            lines.append(f"{i}. {issue['tag']} ({count}条, {issue['pct']:.1f}%)")
        lines.append("")

    if high_priority_count > 0:
        lines.append(f"高优先级问题：{high_priority_count} 条需立即处理")
        lines.append("")

    lines.append(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


def _get_site_url() -> str:
    """获取站点 URL 用于推送链接"""
    import os
    return os.environ.get("SITE_URL", "https://clueai-reviewlens.com").rstrip("/")


def _format_compare_lines(triggered_rules: list[dict]) -> list[str]:
    """从触发规则中提取环比数据，格式化为文本行"""
    lines: list[str] = []
    for rule in triggered_rules:
        compare_data = rule.get("compare_data")
        if not compare_data:
            continue

        metric = compare_data.get("metric", "")
        window = compare_data.get("window_days", 14)

        if metric == "neg_rate":
            prev = compare_data["prev_rate"]
            curr = compare_data["current_rate"]
            delta = compare_data["delta"]
            lines.append(f"▶ 负面率环比（{window}天）")
            lines.append(f"   上期：{prev:.1f}% → 本期：{curr:.1f}%（↑ {delta:.1f}pp，超阈值 {compare_data['threshold']}%）")
            lines.append("")

        elif metric in ("issue_pct", "highlight_pct"):
            label = "问题占比" if metric == "issue_pct" else "亮点"
            changes = compare_data.get("issue_changes", [])
            if changes:
                lines.append(f"▶ {label}环比变化（{window}天）TOP{len(changes[:3])}")
                for i, ch in enumerate(changes[:3], 1):
                    delta = ch["current_pct"] - ch["prev_pct"]
                    arrow = "↑" if delta > 0 else "↓"
                    lines.append(
                        f"   {i}. {ch['tag']}：{ch['prev_pct']:.1f}% → "
                        f"{ch['current_pct']:.1f}%（{arrow} {abs(delta):.1f}pp）({ch['count']}条)"
                    )
                lines.append("")

    return lines


def _format_rich_notification_text(
    session_data: dict,
    top_issues: list[dict],
    high_priority_count: int,
    triggered_rules: list[dict] | None = None,
    ai_summary: str | None = None,
    ai_recommendations: list[str] | None = None,
) -> str:
    """增强版推送文本：包含环比、AI总结、链接"""
    product_id = session_data.get("product_id", "")
    total = session_data.get("total_reviews", 0)
    neg_count = session_data.get("negative_count", 0)
    neg_rate = neg_count / total * 100 if total > 0 else 0
    site_url = _get_site_url()

    lines = [
        f"📊 评论分析完成 | {product_id}",
        "",
        f"本次分析：{total} 条 | 差评率：{neg_rate:.1f}%",
        "",
    ]

    # 触发的规则摘要
    if triggered_rules:
        trigger_names = [r["rule"] for r in triggered_rules if r["rule"] != "新批次自动推送"]
        if trigger_names:
            lines.append(f"⚠️ 触发规则：{' | '.join(trigger_names)}")
            lines.append("")

    if top_issues:
        lines.append("TOP3 核心问题：")
        for i, issue in enumerate(top_issues[:3], 1):
            count = issue.get("count", 0)
            lines.append(f"{i}. {issue['tag']} ({count}条, {issue['pct']:.1f}%)")
        lines.append("")

    # 环比详情
    if triggered_rules:
        compare_lines = _format_compare_lines(triggered_rules)
        if compare_lines:
            lines.extend(compare_lines)

    if high_priority_count > 0:
        lines.append(f"高优先级问题：{high_priority_count} 条需立即处理")
        lines.append("")

    # AI 总结和建议
    if ai_summary:
        lines.append("🤖 AI 总结")
        lines.append(ai_summary)
        lines.append("")

    if ai_recommendations:
        lines.append("💡 AI 建议")
        for i, rec in enumerate(ai_recommendations[:3], 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    # 链接
    lines.append(f"🔗 查看详情 → {site_url}/analysis/results?product_id={product_id}")
    lines.append("")
    lines.append(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


def _build_feishu_body(text: str, secret: str = "") -> dict:
    """构建飞书消息体（支持加签）"""
    body: dict = {
        "msg_type": "text",
        "content": {
            "text": text,
        },
    }

    if secret:
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            msg=b"",
            digestmod=hashlib.sha256,
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        body["timestamp"] = timestamp
        body["sign"] = sign

    return body


def send_feishu_notification(
    webhook_url: str,
    data: dict,
    secret: str = "",
) -> dict:
    """
    飞书群机器人推送。
    data 中需包含 session_data, top_issues, high_priority_count 字段。
    返回 {"ok": True/False, "msg": "..."}
    """
    if not webhook_url:
        return {"ok": False, "msg": "未配置 Webhook URL"}

    session_data = data.get("session_data", {})
    top_issues = data.get("top_issues", [])
    high_priority_count = data.get("high_priority_count", 0)

    text = _format_notification_text(session_data, top_issues, high_priority_count)
    body = _build_feishu_body(text, secret)

    try:
        resp = requests.post(webhook_url, json=body, timeout=FEISHU_TIMEOUT)
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            return {"ok": True, "msg": "推送成功"}
        return {"ok": False, "msg": result.get("msg", "推送失败")}
    except requests.Timeout:
        return {"ok": False, "msg": "推送超时，请检查网络"}
    except Exception as e:
        logger.error(f"飞书推送失败: {e}")
        return {"ok": False, "msg": f"推送异常: {str(e)}"}


def send_notification(
    platform: str,
    webhook_url: str,
    data: dict,
    secret: str = "",
) -> dict:
    """统一入口，根据 platform 参数选择推送方式"""
    if platform == "feishu":
        return send_feishu_notification(webhook_url, data, secret)
    return {"ok": False, "msg": f"不支持的推送平台: {platform}"}


def _test_webhook(webhook_url: str, platform: str = "feishu", secret: str = "") -> dict:
    """测试 Webhook 连接"""
    test_text = "🔔 ClueAI 测试消息\n\nWebhook 连接测试成功！"

    if platform == "feishu":
        body = _build_feishu_body(test_text, secret)
        try:
            resp = requests.post(webhook_url, json=body, timeout=FEISHU_TIMEOUT)
            result = resp.json()
            if result.get("code") == 0 or result.get("StatusCode") == 0:
                return {"ok": True, "msg": "连接成功"}
            return {"ok": False, "msg": result.get("msg", "连接失败")}
        except requests.Timeout:
            return {"ok": False, "msg": "连接超时"}
        except Exception as e:
            return {"ok": False, "msg": f"连接异常: {str(e)}"}

    return {"ok": False, "msg": f"不支持的平台: {platform}"}


# ============================================================
# 推送规则引擎
# ============================================================

def _get_top_issues(comments: list[dict], sentiment_type: str) -> list[dict]:
    """从评论中提取 TOP 标签"""
    tag_field = "highlight_tag" if sentiment_type == "positive" else "issue_tag"
    pool = [c for c in comments if c.get("sentiment") == sentiment_type]
    pool_size = len(pool) if pool else 1

    tag_counter: Counter = Counter()
    for c in pool:
        raw = c.get(tag_field, "")
        if raw:
            seen_in_comment: set[str] = set()
            for tag in raw.split(","):
                tag = tag.strip()
                if tag and tag not in seen_in_comment:
                    seen_in_comment.add(tag)
                    tag_counter[tag] += 1

    return [
        {"tag": tag, "count": count, "pct": count / pool_size * 100}
        for tag, count in tag_counter.most_common(10)
    ]


def _get_prev_neg_rate(
    user_id: int,
    product_id: str,
    current_session_id: int,
    window_days: int,
) -> float | None:
    """取上一批次的负面率，无历史数据时返回 None。"""
    sessions = get_sessions(user_id, product_id)
    cutoff = datetime.now() - timedelta(days=window_days)
    for s in sessions:
        if s["id"] == current_session_id:
            continue
        created = s.get("created_at")
        if created and created < cutoff:
            break
        total = s.get("total_reviews") or 1
        neg = s.get("negative_count") or 0
        return neg / total * 100
    return None


def _get_prev_top_issues(
    user_id: int,
    product_id: str,
    current_session_id: int,
    window_days: int,
    sentiment_type: str,
) -> list[dict]:
    """取上一批次的 TOP 标签列表，无历史数据时返回空列表。"""
    sessions = get_sessions(user_id, product_id)
    cutoff = datetime.now() - timedelta(days=window_days)
    for s in sessions:
        if s["id"] == current_session_id:
            continue
        created = s.get("created_at")
        if created and created < cutoff:
            break
        prev_comments = get_comments(user_id, session_id=s["id"])
        return _get_top_issues(prev_comments, sentiment_type)
    return []


def check_global_rules(
    user_id: int,
    session_id: int,
    session_data: dict,
    comments: list[dict],
    rules_config: dict,
) -> list[dict]:
    """
    检查全局推送规则。
    返回触发的规则列表，每项: {"rule": "规则名", "detail": "详情"}
    """
    triggered = []
    total = session_data.get("total_reviews", 0) or 1
    neg_count = session_data.get("negative_count", 0)
    neg_rate = neg_count / total * 100

    # 问题占比阈值
    if rules_config.get("issue_pct_enabled", False):
        threshold = rules_config.get("issue_pct_threshold", 5)
        top_issues = _get_top_issues(comments, "negative")
        exceeded = [i for i in top_issues if i["pct"] >= threshold]
        if exceeded:
            details = ", ".join([f"「{i['tag']}」{i['count']}条/{i['pct']:.1f}%" for i in exceeded[:3]])
            triggered.append({
                "rule": "问题占比告警",
                "detail": f"以下问题占比超过 {threshold}%：{details}",
            })

    # 负面率阈值
    if rules_config.get("neg_rate_enabled", False):
        threshold = rules_config.get("neg_rate_threshold", 25)
        if neg_rate >= threshold:
            triggered.append({
                "rule": "负面率告警",
                "detail": f"负面率 {neg_rate:.1f}% 超过阈值 {threshold}%",
            })

    # 亮点占比阈值
    if rules_config.get("highlight_pct_enabled", False):
        threshold = rules_config.get("highlight_pct_threshold", 10)
        top_highlights = _get_top_issues(comments, "positive")
        exceeded = [i for i in top_highlights if i["pct"] >= threshold]
        if exceeded:
            details = ", ".join([f"「{i['tag']}」{i['count']}条/{i['pct']:.1f}%" for i in exceeded[:3]])
            triggered.append({
                "rule": "亮点通知",
                "detail": f"以下亮点占比超过 {threshold}%：{details}",
            })

    product_id = session_data.get("product_id", "")

    # 负面率环比突增
    if rules_config.get("neg_rate_compare_enabled", False):
        threshold = rules_config.get("neg_rate_compare_threshold", 5)
        window = int(rules_config.get("neg_rate_compare_window", "14"))
        prev_rate = _get_prev_neg_rate(user_id, product_id, session_id, window)
        if prev_rate is not None:
            delta = neg_rate - prev_rate
            if delta >= threshold:
                triggered.append({
                    "rule": "负面率环比告警",
                    "detail": f"负面率 {neg_rate:.1f}%，较上期 {prev_rate:.1f}% 上升 {delta:.1f} 个百分点",
                    "compare_data": {
                        "metric": "neg_rate",
                        "window_days": window,
                        "prev_rate": round(prev_rate, 1),
                        "current_rate": round(neg_rate, 1),
                        "delta": round(delta, 1),
                        "threshold": threshold,
                    },
                })

    # 问题占比环比突增
    if rules_config.get("issue_compare_enabled", False):
        threshold = rules_config.get("issue_compare_threshold", 3)
        window = int(rules_config.get("issue_compare_window", "14"))
        top_issues = _get_top_issues(comments, "negative")
        prev_issues = _get_prev_top_issues(user_id, product_id, session_id, window, "negative")
        if prev_issues:
            prev_map = {i["tag"]: i["pct"] for i in prev_issues}
            spikes = [
                f"「{i['tag']}」+{i['pct'] - prev_map.get(i['tag'], 0):.1f}%"
                for i in top_issues
                if i["pct"] - prev_map.get(i["tag"], 0) >= threshold
            ]
            issue_changes = [
                {
                    "tag": i["tag"],
                    "prev_pct": round(prev_map.get(i["tag"], 0), 1),
                    "current_pct": round(i["pct"], 1),
                    "count": i.get("count", 0),
                }
                for i in top_issues
                if i["pct"] - prev_map.get(i["tag"], 0) >= threshold
            ]
            if spikes:
                triggered.append({
                    "rule": "问题占比环比告警",
                    "detail": f"以下问题较上期明显增加：{', '.join(spikes[:3])}",
                    "compare_data": {
                        "metric": "issue_pct",
                        "window_days": window,
                        "threshold": threshold,
                        "issue_changes": issue_changes[:5],
                    },
                })

    # 亮点环比变化
    if rules_config.get("highlight_compare_enabled", False):
        threshold = rules_config.get("highlight_compare_threshold", 5)
        window = int(rules_config.get("highlight_compare_window", "14"))
        top_highlights_cur = _get_top_issues(comments, "positive")
        prev_highlights = _get_prev_top_issues(user_id, product_id, session_id, window, "positive")
        if prev_highlights:
            prev_map = {i["tag"]: i["pct"] for i in prev_highlights}
            spikes = [
                f"「{i['tag']}」+{i['pct'] - prev_map.get(i['tag'], 0):.1f}%"
                for i in top_highlights_cur
                if i["pct"] - prev_map.get(i["tag"], 0) >= threshold
            ]
            highlight_changes = [
                {
                    "tag": i["tag"],
                    "prev_pct": round(prev_map.get(i["tag"], 0), 1),
                    "current_pct": round(i["pct"], 1),
                    "count": i.get("count", 0),
                }
                for i in top_highlights_cur
                if i["pct"] - prev_map.get(i["tag"], 0) >= threshold
            ]
            if spikes:
                triggered.append({
                    "rule": "亮点环比通知",
                    "detail": f"以下亮点较上期明显增加：{', '.join(spikes[:3])}",
                    "compare_data": {
                        "metric": "highlight_pct",
                        "window_days": window,
                        "threshold": threshold,
                        "issue_changes": highlight_changes[:5],
                    },
                })

    return triggered


def check_product_rules(
    product_id: str,
    session_data: dict,
    comments: list[dict],
    product_rules: list[dict],
) -> list[dict]:
    """
    检查产品级自定义规则。
    返回触发的规则列表。
    """
    triggered = []
    total = session_data.get("total_reviews", 0) or 1
    neg_count = session_data.get("negative_count", 0)
    neg_rate = neg_count / total * 100

    matching_rules = [
        r for r in product_rules
        if r.get("product_id") == product_id and r.get("enabled", True)
    ]

    for rule in matching_rules:
        # 问题占比
        issue_threshold = rule.get("issue_pct", 5)
        top_issues = _get_top_issues(comments, "negative")
        exceeded = [i for i in top_issues if i["pct"] >= issue_threshold]
        if exceeded:
            details = ", ".join([f"「{i['tag']}」{i['pct']:.1f}%" for i in exceeded[:3]])
            triggered.append({
                "rule": f"产品规则（{product_id}）问题占比",
                "detail": f"问题占比超过 {issue_threshold}%：{details}",
            })

        # 负面率
        neg_threshold = rule.get("neg_rate", 25)
        if neg_rate >= neg_threshold:
            triggered.append({
                "rule": f"产品规则（{product_id}）负面率",
                "detail": f"负面率 {neg_rate:.1f}% 超过阈值 {neg_threshold}%",
            })

        # 亮点占比
        hl_threshold = rule.get("hl_pct", 10)
        top_highlights = _get_top_issues(comments, "positive")
        hl_exceeded = [i for i in top_highlights if i["pct"] >= hl_threshold]
        if hl_exceeded:
            details = ", ".join([f"「{i['tag']}」{i['pct']:.1f}%" for i in hl_exceeded[:3]])
            triggered.append({
                "rule": f"产品规则（{product_id}）亮点通知",
                "detail": f"亮点占比超过 {hl_threshold}%：{details}",
            })

    return triggered


def should_notify(
    user_id: int,
    session_id: int,
    session_data: dict,
    comments: list[dict],
    rules_config: dict,
    product_rules: list[dict],
) -> tuple[bool, list[dict]]:
    """
    综合判断是否需要推送。
    返回: (should_push, triggered_rules)
    """
    triggered = []

    # 新批次自动推送
    if rules_config.get("auto_push_new_batch", False):
        triggered.append({"rule": "新批次自动推送", "detail": "分析完成自动推送摘要"})

    # 全局规则
    triggered.extend(check_global_rules(user_id, session_id, session_data, comments, rules_config))

    # 产品级规则
    product_id = session_data.get("product_id", "")
    if product_id:
        triggered.extend(check_product_rules(product_id, session_data, comments, product_rules))

    return len(triggered) > 0, triggered


def auto_notify_after_analysis(
    user_id: int,
    session_id: int,
) -> dict | None:
    """
    分析完成后的自动推送入口。
    读取用户设置 → 检查规则 → 触发推送（含 AI 总结/建议/链接/环比详情）。
    返回推送结果或 None（不需要推送时）。
    """
    raw_settings = get_setting(user_id, "push_settings")
    if not raw_settings:
        return None

    try:
        settings = json.loads(raw_settings)
    except json.JSONDecodeError:
        return None

    webhook_url = settings.get("webhook_url", "")
    if not webhook_url:
        return None

    session = get_session_by_id(user_id, session_id)
    if not session:
        return None

    comments = get_comments(user_id, session_id=session_id)
    rules_config = settings.get("rules", {})
    product_rules = settings.get("product_rules", [])

    should_push, triggered = should_notify(user_id, session_id, session, comments, rules_config, product_rules)
    if not should_push:
        return None

    # 构建推送数据
    top_issues = _get_top_issues(comments, "negative")
    high_priority_count = sum(1 for c in comments if c.get("priority") == "高")

    # 获取 AI 总结和建议
    ai_summary = None
    ai_recommendations = None
    try:
        from review_analyzer.insight_engine import build_results_insights

        context = {
            "product_id": session.get("product_id", ""),
            "version": session.get("version", ""),
            "time_label": "",
            "workflow_purpose": session.get("workflow_purpose", ""),
        }
        modules = build_results_insights(user_id, comments, context)
        unmet = modules.get("unmet_needs", {})
        if unmet.get("summary"):
            ai_summary = unmet["summary"]
        recs = modules.get("recommendations", {})
        if recs.get("rows"):
            ai_recommendations = [r.get("detail", "") for r in recs["rows"][:3] if r.get("detail")]
    except Exception as e:
        logger.warning(f"获取 AI 总结失败，跳过: {e}")

    # 使用增强版格式化
    text = _format_rich_notification_text(
        session_data=session,
        top_issues=top_issues,
        high_priority_count=high_priority_count,
        triggered_rules=triggered,
        ai_summary=ai_summary,
        ai_recommendations=ai_recommendations,
    )

    secret = settings.get("webhook_secret", "")
    body = _build_feishu_body(text, secret)

    try:
        resp = requests.post(webhook_url, json=body, timeout=FEISHU_TIMEOUT)
        result_json = resp.json()
        if result_json.get("code") == 0 or result_json.get("StatusCode") == 0:
            result = {"ok": True, "msg": "推送成功"}
        else:
            result = {"ok": False, "msg": result_json.get("msg", "推送失败")}
    except requests.Timeout:
        result = {"ok": False, "msg": "推送超时，请检查网络"}
    except Exception as e:
        logger.error(f"飞书推送失败: {e}")
        result = {"ok": False, "msg": f"推送异常: {str(e)}"}

    result["triggered_rules"] = triggered
    return result


def push_selected_items(
    user_id: int,
    webhook_url: str,
    secret: str,
    session_id: int,
    selected_tags: list[str],
    tag_type: str,
) -> dict:
    """
    推送用户勾选的 TOP10 条目到飞书。
    tag_type: "issue" 或 "highlight"
    """
    session = get_session_by_id(user_id, session_id)
    if not session:
        return {"ok": False, "msg": "未找到分析记录"}

    product_id = session.get("product_id", "")
    type_label = "问题" if tag_type == "issue" else "亮点"
    emoji = "⚠️" if tag_type == "issue" else "✅"

    lines = [
        f"{emoji} 产品{type_label}推送 | {product_id}",
        "",
    ]
    for i, tag in enumerate(selected_tags, 1):
        lines.append(f"{i}. {tag}")

    lines.append("")
    lines.append(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")

    text = "\n".join(lines)
    body = _build_feishu_body(text, secret)

    try:
        resp = requests.post(webhook_url, json=body, timeout=FEISHU_TIMEOUT)
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            return {"ok": True, "msg": "推送成功"}
        return {"ok": False, "msg": result.get("msg", "推送失败")}
    except requests.Timeout:
        return {"ok": False, "msg": "推送超时"}
    except Exception as e:
        return {"ok": False, "msg": f"推送异常: {str(e)}"}


# ============================================================
# V5-T3: 富文本分板块推送（post 格式 + @mention）
# ============================================================

def _build_post_body(title: str, content: list[list[dict]], secret: str = "") -> dict:
    """构建飞书 post 富文本消息体"""
    body: dict = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": content,
                },
            },
        },
    }

    if secret:
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            msg=b"",
            digestmod=hashlib.sha256,
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        body["timestamp"] = timestamp
        body["sign"] = sign

    return body


def _build_dept_section(
    dept: str,
    dept_label: str,
    dept_icon: str,
    issues: list[dict],
    contact_open_id: str | None,
    escalated_tags: set[str] | None = None,
) -> list[list[dict]]:
    """构建单个部门板块的富文本行"""
    lines: list[list[dict]] = []

    header_elements: list[dict] = [
        {"tag": "text", "text": f"\n{dept_icon} 【{dept_label}】"},
    ]
    if contact_open_id:
        header_elements.append({"tag": "at", "user_id": contact_open_id})
    lines.append(header_elements)

    for i, issue in enumerate(issues, 1):
        tag = issue.get("tag", "")
        pct = issue.get("pct", 0)
        count = issue.get("count", 0)
        tag_label = issue.get("tag_label", tag)

        text = f"{i}. {tag_label} ({count}条, {pct:.1f}%)"

        if escalated_tags and tag in escalated_tags:
            text += " 🔴⚡已升级"

        lines.append([{"tag": "text", "text": text}])

    return lines


def _get_action_progress(user_id: int, product_id: str | None, top_tag_names: list[str]) -> list[dict]:
    """获取 TOP 问题对应的行动项复盘进度"""
    if not top_tag_names:
        return []
    try:
        from review_analyzer.action_store import ACTION_STATUS_LABELS, get_action_items

        items = get_action_items(user_id)
        results: list[dict] = []
        seen_tags: set[str] = set()
        for item in items:
            tag = item.get("tag_name", "")
            if tag not in top_tag_names or tag in seen_tags:
                continue
            if product_id and item.get("source_product_id") != product_id:
                continue
            status_raw = item.get("status", "todo")
            status_label = ACTION_STATUS_LABELS.get(status_raw, status_raw)
            results.append({"tag": tag, "status": status_label, "status_raw": status_raw})
            seen_tags.add(tag)
        return results
    except Exception:
        return []


def build_rich_push_content(
    product_name: str,
    period_label: str,
    dept_issues: dict[str, list[dict]],
    dept_contacts: dict[str, str] | None = None,
    escalation_results: list[dict] | None = None,
    top_highlights: list[dict] | None = None,
    action_progress: list[dict] | None = None,
    product_id: str | None = None,
) -> tuple[str, list[list[dict]]]:
    """
    构建分板块富文本推送内容。

    参数:
        product_name: 产品名称/SKU
        period_label: 时间范围标签（如 "2026-06-09 ~ 2026-06-14"）
        dept_issues: route_issues_by_department() 的输出
        dept_contacts: {dept: open_id} 部门联系人 open_id
        escalation_results: 升级结果列表
        top_highlights: 亮点 TOP 3
        action_progress: TOP 问题复盘进度
        product_id: 产品 ID，用于生成链接

    返回:
        (title, content_lines) 用于 _build_post_body
    """
    from review_analyzer.department_router import DEPT_ICONS, DEPT_LABELS

    title = f"📊 产品报告 | {product_name} | {period_label}"

    contacts = dept_contacts or {}
    escalated_tags: set[str] = set()
    if escalation_results:
        escalated_tags = {r.get("tag_name", "") for r in escalation_results}

    content: list[list[dict]] = []

    dept_order = ["qa", "product", "ops", "cs", "other"]
    for dept in dept_order:
        issues = dept_issues.get(dept, [])
        if not issues:
            continue

        dept_label = DEPT_LABELS.get(dept, "其他")
        dept_icon = DEPT_ICONS.get(dept, "📋")
        contact_id = contacts.get(dept)

        section_lines = _build_dept_section(
            dept, dept_label, dept_icon, issues, contact_id, escalated_tags
        )
        content.extend(section_lines)

    if escalation_results:
        content.append([{"tag": "text", "text": "\n━━━━━━━━━━━━━━━━━━━━━"}])
        content.append([{"tag": "text", "text": "⚡ 升级行动（已写入行动中心）："}])
        for esc in escalation_results:
            tag_label = esc.get("tag_label", esc.get("tag_name", ""))
            action = esc.get("suggested_action", "")
            timeline = esc.get("expected_timeline", "")
            line = f"• 「{tag_label}」→ {action[:50]}"
            if timeline:
                line += f"，预计{timeline}"
            content.append([{"tag": "text", "text": line}])
        # B4: 行动中心引导
        site_url = _get_site_url()
        content.append([
            {"tag": "text", "text": "🔗 如需修改或增加行动计划，请前往 "},
            {"tag": "a", "text": "行动中心", "href": f"{site_url}/actions"},
        ])

    # B6: TOP 问题复盘进度
    if action_progress:
        content.append([{"tag": "text", "text": "\n━━━━━━━━━━━━━━━━━━━━━"}])
        content.append([{"tag": "text", "text": "📋 TOP 问题复盘进度"}])
        for ap in action_progress:
            suffix = " ✅" if ap.get("status_raw") == "done" else ""
            content.append([{"tag": "text", "text": f"• {ap['tag']} → {ap['status']}{suffix}"}])

    if top_highlights:
        content.append([{"tag": "text", "text": "\n━━━━━━━━━━━━━━━━━━━━━"}])
        hl_parts = []
        for i, hl in enumerate(top_highlights[:3], 1):
            tag_label = hl.get("tag_label", hl.get("tag", ""))
            pct = hl.get("pct", 0)
            count = hl.get("count", 0)
            hl_parts.append(f"{i}. {tag_label} ({count}条, {pct:.1f}%)")
        content.append([{"tag": "text", "text": "✅ 产品亮点 TOP 3："}])
        content.append([{"tag": "text", "text": "  ".join(hl_parts)}])

    # B3: 详情链接
    site_url = _get_site_url()
    link_line: list[dict] = [{"tag": "text", "text": "\n🔗 "}]
    if product_id:
        link_line.append({"tag": "a", "text": "查看完整分析", "href": f"{site_url}/analysis/results?product_id={product_id}"})
        link_line.append({"tag": "text", "text": " | "})
    link_line.append({"tag": "a", "text": "行动中心", "href": f"{site_url}/actions"})
    content.append(link_line)

    return title, content


def send_rich_push(
    webhook_url: str,
    product_name: str,
    period_label: str,
    dept_issues: dict[str, list[dict]],
    dept_contacts: dict[str, str] | None = None,
    escalation_results: list[dict] | None = None,
    top_highlights: list[dict] | None = None,
    secret: str = "",
    action_progress: list[dict] | None = None,
    product_id: str | None = None,
) -> dict:
    """发送富文本分板块推送到飞书"""
    if not webhook_url:
        return {"ok": False, "msg": "未配置 Webhook URL"}

    title, content = build_rich_push_content(
        product_name=product_name,
        period_label=period_label,
        dept_issues=dept_issues,
        dept_contacts=dept_contacts,
        escalation_results=escalation_results,
        top_highlights=top_highlights,
        action_progress=action_progress,
        product_id=product_id,
    )

    body = _build_post_body(title, content, secret)

    try:
        resp = requests.post(webhook_url, json=body, timeout=FEISHU_TIMEOUT)
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            return {"ok": True, "msg": "推送成功"}
        return {"ok": False, "msg": result.get("msg", "推送失败")}
    except requests.Timeout:
        return {"ok": False, "msg": "推送超时，请检查网络"}
    except Exception as e:
        logger.error(f"飞书富文本推送失败: {e}")
        return {"ok": False, "msg": f"推送异常: {str(e)}"}
