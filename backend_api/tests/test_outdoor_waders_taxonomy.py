from __future__ import annotations

import json
from pathlib import Path

import yaml

from backend_api.app.services import taxonomy_loader
from backend_api.app.services.category_grouper import aspects_to_legacy_schema
from backend_api.app.services.sub_category_inference import infer_sub_category_from_payload

ROOT = Path(__file__).resolve().parent.parent.parent


def _load_waders_taxonomy() -> dict:
    path = ROOT / "data" / "taxonomy" / "v1.0" / "outdoor" / "waders.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_waders_taxonomy_yaml_shape() -> None:
    data = _load_waders_taxonomy()
    aspects = data["aspects"]
    keys = [item["key"] for item in aspects]

    assert data["sub_category"] == "waders"
    assert data["aspect_count"] == len(aspects) == 21
    assert len(keys) == len(set(keys))
    assert keys[-1] == "other"
    assert {
        "waterproof",
        "seam_integrity",
        "boot_fit",
        "mobility",
        "accessory_storage",
    } <= set(keys)
    assert all(item.get("boundary_note") for item in aspects)


def test_waders_static_mapping() -> None:
    path = ROOT / "backend_api" / "app" / "data" / "sub_category_categories.json"
    mapping = json.loads(path.read_text(encoding="utf-8"))

    assert mapping["sub_category_to_category"]["waders"] == "outdoor"
    assert mapping["sub_category_display_names"]["waders"] == "涉水裤"
    assert mapping["sub_category_display_names_en"]["waders"] == "Waders"
    assert mapping["total_sub_categories"] == 89


def test_wader_sub_category_inference() -> None:
    assert infer_sub_category_from_payload({"category": "Wader"}, "") == "waders"
    assert infer_sub_category_from_payload({"product_name": "Kids chest waders for fishing"}, "") == "waders"
    assert infer_sub_category_from_payload({}, "bootfoot-wader-size-10") == "waders"
    assert infer_sub_category_from_payload({"product_name": "Water shoes for beach"}, "") is None


def test_waders_resolve_aspects_from_db_rows(monkeypatch) -> None:
    data = _load_waders_taxonomy()
    rows = tuple(
        (item["key"], item["label_zh"], item["boundary_note"])
        for item in data["aspects"]
    )

    def fake_load_aspects_from_db(sub_category: str) -> tuple[tuple[str, str, str], ...]:
        return rows if sub_category == "waders" else ()

    monkeypatch.setattr(taxonomy_loader, "_load_aspects_from_db", fake_load_aspects_from_db)

    aspects, hit = taxonomy_loader.resolve_aspects("waders")
    keys = [item["key"] for item in aspects]

    assert hit
    assert keys[-1] == "other"
    assert keys.count("other") == 1
    assert "seam_integrity" in keys
    assert "accessory_storage" in keys


def test_waders_aspect_labels_and_category_mapping() -> None:
    result = aspects_to_legacy_schema(
        aspects=[
            {
                "key": "seam_integrity",
                "polarity": "negative",
                "evidence_span": "leaked along the leg seams",
                "evidence_level": "certain",
            }
        ],
        sentiment="negative",
        content="The waders leaked along the leg seams the first time I used them.",
        pain_points=["leaked along the leg seams"],
        highlights=[],
    )

    assert result["category"] == "product_quality"
    assert result["priority"] == "高"
    assert result["issue_tag"] == "Seam Integrity"
