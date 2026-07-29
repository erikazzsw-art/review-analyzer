from __future__ import annotations

from backend_api.app.routes.analytics import (
    _aggregate_cache_layers_from_jobs,
    _build_job_cost_rankings,
    _build_model_cost_changes,
)


def test_job_cost_rankings_include_total_and_per_review_costs() -> None:
    rankings = _build_job_cost_rankings(
        [
            {
                "id": 101,
                "status": "done",
                "total_rows": 10,
                "session_id": 201,
                "product_id": "A",
                "created_at": "2026-07-29 10:00:00",
                "completed_at": "2026-07-29 10:01:00",
                "trace_json": {
                    "review_count": 10,
                    "llm_calls": 2,
                    "cache_hits": 8,
                    "total_cost_yuan": 0.12,
                    "decisions": [
                        {"name": "llm_prompt_quality", "details": {"model_counts": {"gpt-4o-mini": 2}}},
                    ],
                },
            },
            {
                "id": 102,
                "status": "done",
                "total_rows": 30,
                "session_id": 202,
                "product_id": "B",
                "created_at": "2026-07-29 11:00:00",
                "completed_at": "2026-07-29 11:01:00",
                "trace_json": {
                    "review_count": 30,
                    "llm_calls": 3,
                    "cache_hits": 27,
                    "total_cost_yuan": 0.06,
                    "decisions": [
                        {"name": "llm_prompt_quality", "details": {"model_counts": {"deepseek-chat": 3}}},
                    ],
                },
            },
        ]
    )

    assert rankings["summary"]["total_review_count"] == 40
    assert rankings["summary"]["avg_cost_per_review"] == 0.0045
    assert rankings["job_rankings"][0]["job_id"] == 101
    assert rankings["job_rankings"][0]["total_cost_yuan"] == 0.12
    assert rankings["cost_per_review_rankings"][0]["job_id"] == 101


def test_model_cost_changes_detect_dominant_model_switch() -> None:
    changes = _build_model_cost_changes(
        [
            {"date": "2026-07-28", "model_name": "deepseek-chat", "total_cost_yuan": 1.2},
            {"date": "2026-07-28", "model_name": "gpt-4o-mini", "total_cost_yuan": 0.2},
            {"date": "2026-07-29", "model_name": "deepseek-chat", "total_cost_yuan": 0.1},
            {"date": "2026-07-29", "model_name": "gpt-4o-mini", "total_cost_yuan": 2.0},
        ]
    )

    assert changes == [
        {
            "date": "2026-07-29",
            "previous_date": "2026-07-28",
            "previous_dominant_model": "deepseek-chat",
            "current_dominant_model": "gpt-4o-mini",
            "previous_bucket_cost_yuan": 1.4,
            "current_bucket_cost_yuan": 2.1,
            "total_cost_delta_yuan": 0.7,
            "current_model_cost_delta_yuan": 1.8,
        }
    ]


def test_cache_layers_split_hit_sources_and_miss_reasons() -> None:
    layered = _aggregate_cache_layers_from_jobs(
        [
            {
                "trace_json": {
                    "decisions": [
                        {
                            "name": "cache_lookup",
                            "details": {
                                "checked_count": 12,
                                "hit_count": 7,
                                "miss_count": 5,
                                "hit_levels": {"L1": 4, "L3": 3},
                                "hit_sources": {
                                    "user_history": 2,
                                    "global_review_pool": 2,
                                    "semantic_similar": 3,
                                },
                                "miss_reasons": {
                                    "embedding_missing": 3,
                                    "semantic_similarity_below_threshold": 2,
                                },
                            },
                        },
                        {
                            "name": "clustering",
                            "details": {
                                "saved_llm_calls": 4,
                                "propagated_count": 4,
                            },
                        },
                    ]
                }
            }
        ]
    )

    layers = {item["key"]: item["count"] for item in layered["layers"]}
    reasons = {item["reason"]: item["count"] for item in layered["miss_reasons"]}

    assert layered["checked_count"] == 12
    assert layers["l1_exact_hash"] == 4
    assert layers["user_history"] == 2
    assert layers["global_review_pool"] == 2
    assert layers["semantic_similar"] == 3
    assert layers["cluster_saved"] == 4
    assert reasons["embedding_missing"] == 3
    assert reasons["semantic_similarity_below_threshold"] == 2
