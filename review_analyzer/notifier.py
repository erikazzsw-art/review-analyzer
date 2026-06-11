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
            lines.append(f"{i}. {issue['tag']} ({issue['pct']:.1f}%)")
        lines.append("")

    if high_priority_count > 0:
        lines.append(f"高优先级问题：{high_priority_count} 条需立即处理")
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
            details = ", ".join([f"「{i['tag']}」{i['pct']:.1f}%" for i in exceeded[:3]])
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
            details = ", ".join([f"「{i['tag']}」{i['pct']:.1f}%" for i in exceeded[:3]])
            triggered.append({
                "rule": "亮点通知",
                "detail": f"以下亮点占比超过 {threshold}%：{details}",
            })

    product_id = session_data.get("product_id", "")

    # 负面率环比突增
    if rules_config.get("neg_rate_compare_enabled", False):
        threshold = rules_config.get("neg_rate_compare_threshold", 5)
        window = int(rules_config.get("neg_rate_compare_window", "30"))
        prev_rate = _get_prev_neg_rate(user_id, product_id, session_id, window)
        if prev_rate is not None:
            delta = neg_rate - prev_rate
            if delta >= threshold:
                triggered.append({
                    "rule": "负面率环比告警",
                    "detail": f"负面率 {neg_rate:.1f}%，较上期 {prev_rate:.1f}% 上升 {delta:.1f} 个百分点",
                })

    # 问题占比环比突增
    if rules_config.get("issue_compare_enabled", False):
        threshold = rules_config.get("issue_compare_threshold", 3)
        window = int(rules_config.get("issue_compare_window", "30"))
        top_issues = _get_top_issues(comments, "negative")
        prev_issues = _get_prev_top_issues(user_id, product_id, session_id, window, "negative")
        if prev_issues:
            prev_map = {i["tag"]: i["pct"] for i in prev_issues}
            spikes = [
                f"「{i['tag']}」+{i['pct'] - prev_map.get(i['tag'], 0):.1f}%"
                for i in top_issues
                if i["pct"] - prev_map.get(i["tag"], 0) >= threshold
            ]
            if spikes:
                triggered.append({
                    "rule": "问题占比环比告警",
                    "detail": f"以下问题较上期明显增加：{', '.join(spikes[:3])}",
                })

    # 亮点环比变化
    if rules_config.get("highlight_compare_enabled", False):
        threshold = rules_config.get("highlight_compare_threshold", 5)
        window = int(rules_config.get("highlight_compare_window", "30"))
        top_highlights_cur = _get_top_issues(comments, "positive")
        prev_highlights = _get_prev_top_issues(user_id, product_id, session_id, window, "positive")
        if prev_highlights:
            prev_map = {i["tag"]: i["pct"] for i in prev_highlights}
            spikes = [
                f"「{i['tag']}」+{i['pct'] - prev_map.get(i['tag'], 0):.1f}%"
                for i in top_highlights_cur
                if i["pct"] - prev_map.get(i["tag"], 0) >= threshold
            ]
            if spikes:
                triggered.append({
                    "rule": "亮点环比通知",
                    "detail": f"以下亮点较上期明显增加：{', '.join(spikes[:3])}",
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
    读取用户设置 → 检查规则 → 触发推送。
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

    data = {
        "session_data": session,
        "top_issues": top_issues,
        "high_priority_count": high_priority_count,
        "triggered_rules": triggered,
    }

    secret = settings.get("webhook_secret", "")
    result = send_feishu_notification(webhook_url, data, secret)
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
