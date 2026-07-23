"""V5-T3 Step 4-5 单元测试：LLM 行动建议 + 富文本推送"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from review_analyzer.notifier import (
    _build_post_body,
    build_rich_push_content,
)


class TestBuildPostBody:
    def test_basic_structure(self):
        body = _build_post_body("测试标题", [[{"tag": "text", "text": "hello"}]])
        assert body["msg_type"] == "post"
        assert body["content"]["post"]["zh_cn"]["title"] == "测试标题"
        assert body["content"]["post"]["zh_cn"]["content"] == [[{"tag": "text", "text": "hello"}]]

    def test_no_secret_no_sign(self):
        body = _build_post_body("t", [[]])
        assert "timestamp" not in body
        assert "sign" not in body


class TestBuildRichPushContent:
    def test_basic_output(self):
        dept_issues = {
            "qa": [
                {"tag": "packaging", "pct": 15.2, "tag_label": "包装"},
                {"tag": "shipping_damage", "pct": 8.0, "tag_label": "运输损坏"},
            ],
            "product": [
                {"tag": "aesthetics", "pct": 7.1, "tag_label": "外观设计"},
            ],
            "ops": [],
            "cs": [],
            "other": [],
        }

        title, content = build_rich_push_content(
            product_name="SKU-001",
            period_label="2026-06-09 ~ 2026-06-14",
            dept_issues=dept_issues,
        )

        assert "SKU-001" in title
        assert len(content) > 0

        all_text = " ".join(
            elem.get("text", "") for line in content for elem in line
        )
        assert "质检" in all_text
        assert "产品总负责人" in all_text
        assert "问题归属" in all_text
        assert "包装" in all_text
        assert "15.2%" in all_text

    def test_with_at_mention(self):
        dept_issues = {
            "qa": [{"tag": "packaging", "pct": 15.0, "tag_label": "包装"}],
            "product": [],
            "ops": [],
            "cs": [],
            "other": [],
        }
        dept_contacts = {"qa": "ou_abc123", "ops": "ou_ops_owner"}

        title, content = build_rich_push_content(
            product_name="TEST",
            period_label="2026-06-14",
            dept_issues=dept_issues,
            dept_contacts=dept_contacts,
        )

        has_at = any(
            elem.get("tag") == "at" and elem.get("user_id") == "ou_abc123"
            for line in content
            for elem in line
        )
        has_product_owner_at = any(
            elem.get("tag") == "at" and elem.get("user_id") == "ou_ops_owner"
            for line in content
            for elem in line
        )
        assert has_at
        assert has_product_owner_at

    def test_with_escalation(self):
        dept_issues = {
            "qa": [{"tag": "packaging", "pct": 15.0, "tag_label": "包装"}],
            "product": [],
            "ops": [],
            "cs": [],
            "other": [],
        }
        escalation_results = [
            {
                "tag_name": "packaging",
                "tag_label": "包装",
                "suggested_action": "更换供应商缓冲材料",
                "expected_timeline": "2周后",
            }
        ]

        title, content = build_rich_push_content(
            product_name="TEST",
            period_label="2026-06-14",
            dept_issues=dept_issues,
            escalation_results=escalation_results,
        )

        all_text = " ".join(
            elem.get("text", "") for line in content for elem in line
        )
        assert "已升级" in all_text
        assert "升级行动" in all_text
        assert "已写入行动中心，并提醒对应责任方处理" in all_text
        assert "更换供应商缓冲材料" in all_text

    def test_with_highlights(self):
        dept_issues = {"qa": [], "product": [], "ops": [], "cs": [], "other": []}
        highlights = [
            {"tag": "aesthetics", "pct": 25.1, "tag_label": "外观好看"},
            {"tag": "assembly", "pct": 18.3, "tag_label": "安装简便"},
        ]

        title, content = build_rich_push_content(
            product_name="TEST",
            period_label="2026-06-14",
            dept_issues=dept_issues,
            top_highlights=highlights,
        )

        all_text = " ".join(
            elem.get("text", "") for line in content for elem in line
        )
        assert "亮点" in all_text
        assert "外观好看" in all_text

    def test_empty_departments_skipped(self):
        dept_issues = {"qa": [], "product": [], "ops": [], "cs": [], "other": []}

        title, content = build_rich_push_content(
            product_name="TEST",
            period_label="2026-06-14",
            dept_issues=dept_issues,
        )

        all_text = " ".join(
            elem.get("text", "") for line in content for elem in line
        )
        assert "质检" not in all_text
        assert "产研" not in all_text


class TestActionAdvisor:
    @patch("backend_api.app.services.action_advisor._get_router")
    def test_generate_action_advice_success(self, mock_get_router):
        import json

        mock_router = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "action_title": "优化包装缓冲材料",
            "suggested_action": "更换供应商泡沫材料为EPE珍珠棉",
            "expected_timeline": "2周后",
            "priority": "high",
        })
        mock_router.completion.return_value = (mock_response, "deepseek")
        mock_get_router.return_value = mock_router

        from backend_api.app.services.action_advisor import generate_action_advice

        result = generate_action_advice(
            tag_name="packaging",
            dept="qa",
            current_pct=15.2,
            consecutive_count=3,
            pct_trend=[12.0, 14.0, 15.2],
            product_name="测试桌子",
            sample_reviews=["包装太薄了", "到手就碎了"],
        )

        assert result is not None
        assert result["action_title"] == "优化包装缓冲材料"
        assert result["priority"] == "high"

    @patch("backend_api.app.services.action_advisor._get_router")
    def test_generate_action_advice_llm_error(self, mock_get_router):
        mock_router = MagicMock()
        mock_router.completion.side_effect = RuntimeError("All models failed")
        mock_get_router.return_value = mock_router

        from backend_api.app.services.action_advisor import generate_action_advice

        result = generate_action_advice(
            tag_name="packaging",
            dept="qa",
            current_pct=15.2,
            consecutive_count=3,
            pct_trend=[12.0, 14.0, 15.2],
        )

        assert result is None
