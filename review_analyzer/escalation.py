"""升级判定引擎 — 连续多期 TOP 问题自动升级"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from review_analyzer.department_router import get_issue_dept
from review_analyzer.push_snapshot_store import (
    get_escalation_states,
    get_recent_snapshots,
    reset_escalation_count,
    upsert_escalation_state,
)


@dataclass
class EscalationConfig:
    consecutive_count: int = 3
    top_n: int = 3
    pct_threshold: float = 10.0


@dataclass
class EscalationResult:
    tag_name: str
    dept: str
    consecutive_count: int
    current_pct: float
    should_escalate: bool
    reason: str


def check_escalations(
    user_id: int,
    product_id: int | None,
    current_snapshot_issues: list[dict],
    config: EscalationConfig | None = None,
) -> list[EscalationResult]:
    """
    检查当前快照中的 issues 是否触发升级。

    逻辑：
    1. 读取最近 N 条 push_snapshots（不含当前）
    2. 对 current_snapshot_issues 中 TOP K 或占比超阈值的 tag：
       检查是否连续 N-1 期也满足条件（加上当前期 = 连续 N 期）
    3. 已升级且 action_item 未完结的 tag 不重复升级
    """
    if config is None:
        config = EscalationConfig()

    recent_snapshots = get_recent_snapshots(
        user_id, product_id, limit=config.consecutive_count - 1
    )

    escalation_states = get_escalation_states(user_id, product_id)
    state_map = {s["tag_name"]: s for s in escalation_states}

    results: list[EscalationResult] = []

    for issue in current_snapshot_issues:
        tag = issue.get("tag", "")
        pct = float(issue.get("pct", 0))
        rank = issue.get("rank", 999)

        qualifies_current = rank <= config.top_n or pct >= config.pct_threshold
        if not qualifies_current:
            continue

        consecutive = 1
        for snapshot in recent_snapshots:
            snap_issues = snapshot.get("top_issues") or []
            if isinstance(snap_issues, str):
                import json
                snap_issues = json.loads(snap_issues)
            found = _tag_qualifies_in_snapshot(
                tag, snap_issues, config.top_n, config.pct_threshold
            )
            if found:
                consecutive += 1
            else:
                break

        if consecutive < config.consecutive_count:
            continue

        existing_state = state_map.get(tag)
        if existing_state and _is_already_escalated(existing_state):
            continue

        reason = "top_n" if rank <= config.top_n else "pct_threshold"
        dept = get_issue_dept(tag)

        results.append(
            EscalationResult(
                tag_name=tag,
                dept=dept,
                consecutive_count=consecutive,
                current_pct=pct,
                should_escalate=True,
                reason=reason,
            )
        )

    return results


def update_escalation_states(
    user_id: int,
    product_id: int | None,
    snapshot_id: int,
    top_issues: list[dict],
    user_mapping: dict[str, str] | None = None,
) -> None:
    """
    快照写入后调用：更新每个 tag 的 consecutive_count。
    - 在本期 top_issues 中的 tag：consecutive_count += 1
    - 不在本期 top_issues 中的 tag：consecutive_count 重置为 0
    """
    current_tags = {issue.get("tag", "") for issue in top_issues}

    existing_states = get_escalation_states(user_id, product_id)
    existing_tags = {s["tag_name"] for s in existing_states}

    for issue in top_issues:
        tag = issue.get("tag", "")
        if not tag:
            continue
        dept = get_issue_dept(tag, user_mapping)

        prev_state = next(
            (s for s in existing_states if s["tag_name"] == tag), None
        )
        prev_count = prev_state["consecutive_count"] if prev_state else 0
        new_count = prev_count + 1

        upsert_escalation_state(
            user_id, product_id, tag, dept, new_count, snapshot_id
        )

    for tag in existing_tags - current_tags:
        reset_escalation_count(user_id, product_id, tag)


def _tag_qualifies_in_snapshot(
    tag: str,
    snap_issues: list[dict],
    top_n: int,
    pct_threshold: float,
) -> bool:
    """检查某个 tag 在历史快照中是否满足 TOP N 或占比阈值"""
    for i, issue in enumerate(snap_issues):
        if issue.get("tag") == tag:
            rank = issue.get("rank", i + 1)
            pct = float(issue.get("pct", 0))
            return rank <= top_n or pct >= pct_threshold
    return False


def _is_already_escalated(state: dict[str, Any]) -> bool:
    """判断该 tag 是否已升级且 action_item 尚未完结"""
    if not state.get("action_item_id"):
        return False
    return bool(state.get("escalated_at"))
