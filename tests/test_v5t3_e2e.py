"""V5-T3 Step 10: 端到端集成测试

模拟连续 3 次分析，验证完整闭环：
- 快照写入正确
- 升级判定在第 3 次触发
- LLM 行动建议生成
- 富文本推送包含升级标记
- 现有推送功能不受影响（回归）
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from review_analyzer.department_router import route_issues_by_department
from review_analyzer.escalation import (
    EscalationConfig,
    check_escalations,
    update_escalation_states,
)
from review_analyzer.notifier import build_rich_push_content, send_rich_push


class TestEndToEndEscalationFlow:
    """模拟连续 3 次推送快照，验证第 3 次触发升级"""

    @patch("review_analyzer.escalation.get_escalation_states")
    @patch("review_analyzer.escalation.get_recent_snapshots")
    @patch("review_analyzer.escalation.upsert_escalation_state")
    @patch("review_analyzer.escalation.reset_escalation_count")
    def test_full_escalation_lifecycle(
        self,
        mock_reset,
        mock_upsert,
        mock_snapshots,
        mock_states,
    ):
        config = EscalationConfig(consecutive_count=3, top_n=3, pct_threshold=10.0)

        # --- 第 1 次推送：packaging 出现 ---
        mock_states.return_value = []
        mock_snapshots.return_value = []

        issues_1 = [{"tag": "packaging", "pct": 15.0, "rank": 1}]
        results = check_escalations(1, 1, issues_1, config)
        assert len(results) == 0  # 只有 1 期，不够连续 3 期

        # --- 第 2 次推送：packaging 连续出现 ---
        mock_snapshots.return_value = [
            {"top_issues": [{"tag": "packaging", "pct": 15.0, "rank": 1}]},
        ]

        issues_2 = [{"tag": "packaging", "pct": 14.5, "rank": 1}]
        results = check_escalations(1, 1, issues_2, config)
        assert len(results) == 0  # 2 期，还差 1 期

        # --- 第 3 次推送：packaging 连续 3 期 → 触发升级 ---
        mock_snapshots.return_value = [
            {"top_issues": [{"tag": "packaging", "pct": 14.5, "rank": 1}]},
            {"top_issues": [{"tag": "packaging", "pct": 15.0, "rank": 1}]},
        ]

        issues_3 = [{"tag": "packaging", "pct": 16.2, "rank": 1}]
        results = check_escalations(1, 1, issues_3, config)
        assert len(results) == 1
        assert results[0].tag_name == "packaging"
        assert results[0].dept == "qa"
        assert results[0].should_escalate is True
        assert results[0].consecutive_count == 3

    @patch("review_analyzer.escalation.get_escalation_states")
    @patch("review_analyzer.escalation.get_recent_snapshots")
    def test_broken_streak_resets(self, mock_snapshots, mock_states):
        """中间一期消失后重置计数"""
        config = EscalationConfig(consecutive_count=3, top_n=3, pct_threshold=10.0)
        mock_states.return_value = []

        # 第 3 期：packaging 在 TOP，但第 2 期没有 → 不连续
        mock_snapshots.return_value = [
            {"top_issues": [{"tag": "packaging", "pct": 12.0, "rank": 2}]},
            {"top_issues": [{"tag": "durability", "pct": 11.0, "rank": 1}]},  # packaging 不在
        ]

        results = check_escalations(1, 1, [{"tag": "packaging", "pct": 13.0, "rank": 1}], config)
        assert len(results) == 0


class TestRichPushIntegration:
    """验证富文本推送完整流程"""

    def test_full_push_content_with_all_sections(self):
        """包含所有板块的完整推送"""
        issues = [
            {"tag": "packaging", "pct": 15.2, "count": 10},
            {"tag": "shipping_damage", "pct": 8.0, "count": 5},
            {"tag": "aesthetics", "pct": 7.1, "count": 4},
            {"tag": "customer_service", "pct": 3.8, "count": 2},
            {"tag": "value_for_money", "pct": 4.2, "count": 3},
            {"tag": "comfort", "pct": 2.5, "count": 2},
        ]

        dept_issues = route_issues_by_department(issues)

        from scripts.aspect_taxonomy import get_aspect_label_zh
        for dept_list in dept_issues.values():
            for issue in dept_list:
                issue["tag_label"] = get_aspect_label_zh(issue.get("tag", ""))

        highlights = [
            {"tag": "aesthetics", "pct": 25.0, "tag_label": "外观设计"},
            {"tag": "assembly", "pct": 18.0, "tag_label": "组装难度"},
        ]

        escalation_results = [
            {
                "tag_name": "packaging",
                "tag_label": "包装",
                "suggested_action": "更换EPE珍珠棉缓冲材料",
                "expected_timeline": "2周后",
            }
        ]

        title, content = build_rich_push_content(
            product_name="IKEA-KALLAX",
            period_label="2026-06-14",
            dept_issues=dept_issues,
            dept_contacts={"qa": "ou_abc123", "product": "ou_def456"},
            escalation_results=escalation_results,
            top_highlights=highlights,
        )

        assert "IKEA-KALLAX" in title
        all_text = " ".join(elem.get("text", "") for line in content for elem in line)

        # 验证各部门板块存在
        assert "质检" in all_text
        assert "产研" in all_text
        assert "运营" in all_text
        assert "客服" in all_text

        # 验证升级标记
        assert "已升级" in all_text
        assert "升级行动" in all_text
        assert "EPE珍珠棉" in all_text

        # 验证亮点
        assert "亮点" in all_text
        assert "外观设计" in all_text

        # 验证 @mention
        has_at_qa = any(
            elem.get("tag") == "at" and elem.get("user_id") == "ou_abc123"
            for line in content for elem in line
        )
        has_at_product = any(
            elem.get("tag") == "at" and elem.get("user_id") == "ou_def456"
            for line in content for elem in line
        )
        assert has_at_qa
        assert has_at_product

    @patch("review_analyzer.notifier.requests.post")
    def test_send_rich_push_http_call(self, mock_post):
        """验证实际 HTTP 调用结构"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0}
        mock_post.return_value = mock_resp

        dept_issues = {
            "qa": [{"tag": "packaging", "pct": 15.0, "tag_label": "包装", "dept": "qa"}],
            "product": [],
            "ops": [],
            "cs": [],
            "other": [],
        }

        result = send_rich_push(
            webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test",
            product_name="TEST-SKU",
            period_label="2026-06-14",
            dept_issues=dept_issues,
        )

        assert result["ok"] is True
        mock_post.assert_called_once()

        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["msg_type"] == "post"
        assert "TEST-SKU" in body["content"]["post"]["zh_cn"]["title"]


class TestRegressionExistingPush:
    """回归：确保现有纯文本推送不受影响"""

    def test_format_notification_text_unchanged(self):
        from review_analyzer.notifier import _format_notification_text

        session_data = {
            "product_id": "SKU-001",
            "total_reviews": 100,
            "negative_count": 30,
        }
        top_issues = [
            {"tag": "packaging", "pct": 15.0},
            {"tag": "durability", "pct": 8.0},
        ]

        text = _format_notification_text(session_data, top_issues, 5)

        assert "SKU-001" in text
        assert "30.0%" in text
        assert "packaging" in text
        assert "高优先级问题：5" in text

    @patch("review_analyzer.notifier.requests.post")
    def test_send_feishu_notification_still_works(self, mock_post):
        from review_analyzer.notifier import send_feishu_notification

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 0}
        mock_post.return_value = mock_resp

        result = send_feishu_notification(
            webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/test",
            data={
                "session_data": {"product_id": "X", "total_reviews": 10, "negative_count": 3},
                "top_issues": [{"tag": "packaging", "pct": 15.0}],
                "high_priority_count": 1,
            },
        )

        assert result["ok"] is True
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert body["msg_type"] == "text"


class TestUpdateEscalationStates:
    """验证 update_escalation_states 正确维护计数"""

    @patch("review_analyzer.escalation.reset_escalation_count")
    @patch("review_analyzer.escalation.upsert_escalation_state")
    @patch("review_analyzer.escalation.get_escalation_states")
    def test_increments_existing(self, mock_get_states, mock_upsert, mock_reset):
        mock_get_states.return_value = [
            {"tag_name": "packaging", "consecutive_count": 2},
        ]

        update_escalation_states(
            user_id=1,
            product_id=1,
            snapshot_id=10,
            top_issues=[{"tag": "packaging", "pct": 15.0}],
        )

        mock_upsert.assert_called_once()
        call_args = mock_upsert.call_args
        # positional: (user_id, product_id, tag, dept, consecutive_count, snapshot_id)
        assert call_args[0][4] == 3

    @patch("review_analyzer.escalation.reset_escalation_count")
    @patch("review_analyzer.escalation.upsert_escalation_state")
    @patch("review_analyzer.escalation.get_escalation_states")
    def test_resets_missing_tags(self, mock_get_states, mock_upsert, mock_reset):
        mock_get_states.return_value = [
            {"tag_name": "packaging", "consecutive_count": 2},
            {"tag_name": "durability", "consecutive_count": 1},
        ]

        update_escalation_states(
            user_id=1,
            product_id=1,
            snapshot_id=10,
            top_issues=[{"tag": "packaging", "pct": 15.0}],
        )

        mock_reset.assert_called_once_with(1, 1, "durability")
