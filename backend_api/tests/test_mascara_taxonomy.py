from __future__ import annotations

import json
from pathlib import Path

import yaml

from backend_api.app.services.category_grouper import aspects_to_legacy_schema
from backend_api.app.services.sub_category_inference import infer_sub_category_from_payload


ROOT = Path(__file__).resolve().parent.parent.parent


def test_mascara_taxonomy_yaml_shape() -> None:
    path = ROOT / "data" / "taxonomy" / "v1.0" / "beauty" / "睫毛膏.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    aspects = data["aspects"]
    keys = [item["key"] for item in aspects]

    assert data["sub_category"] == "睫毛膏"
    assert data["aspect_count"] == len(aspects) == 18
    assert keys[-1] == "other"
    assert {"lengthening_effect", "smudge_resistance", "brush_applicator"} <= set(keys)
    assert all(item.get("boundary_note") for item in aspects)


def test_mascara_sub_category_inference() -> None:
    assert infer_sub_category_from_payload({}, "tarte-睫毛膏-2585628") == "睫毛膏"
    assert infer_sub_category_from_payload({"category": "Mascara"}, "") == "睫毛膏"
    assert infer_sub_category_from_payload({"product_name": "Tarte tubing mascara"}, "") == "睫毛膏"
    assert infer_sub_category_from_payload({"product_name": "Face cream"}, "") is None


def test_mascara_aspect_labels_and_category_mapping() -> None:
    result = aspects_to_legacy_schema(
        aspects=[
            {
                "key": "smudge_resistance",
                "polarity": "negative",
                "evidence_span": "smudges under my eyes",
                "evidence_level": "certain",
            }
        ],
        sentiment="negative",
        content="This mascara smudges under my eyes after two hours.",
        pain_points=["smudges under my eyes"],
        highlights=[],
    )

    assert result["category"] == "product_quality"
    assert result["priority"] == "高"
    assert result["issue_tag"] == "Smudge Resistance"


def test_aspect_labels_json_contains_mascara_labels() -> None:
    path = ROOT / "backend_api" / "app" / "i18n" / "aspect_labels.json"
    labels = json.loads(path.read_text(encoding="utf-8"))

    assert labels["lengthening_effect"]["en"] == "Lengthening Effect"
    assert labels["waterproof_performance"]["zh"] == "防水性"
