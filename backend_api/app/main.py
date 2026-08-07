from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend_api.app.config import get_settings
from backend_api.app.middleware import AnalyticsMiddleware
from backend_api.app.middleware.geo_block import GeoBlockMiddleware
from backend_api.app.routes.actions import router as actions_router
from backend_api.app.routes.actions import trackers_router as trackers_router
from backend_api.app.routes.admin import router as admin_router
from backend_api.app.routes.analysis import router as analysis_router
from backend_api.app.routes.analytics import router as analytics_router
from backend_api.app.routes.asin_watchlist import router as asin_watchlist_router
from backend_api.app.routes.auth import router as auth_router
from backend_api.app.routes.calibration import router as calibration_router
from backend_api.app.routes.compare import router as compare_router
from backend_api.app.routes.copywriter import router as copywriter_router
from backend_api.app.routes.downloads import router as downloads_router
from backend_api.app.routes.export import router as export_router
from backend_api.app.routes.feedback import router as feedback_router
from backend_api.app.routes.golden_set import router as golden_set_router
from backend_api.app.routes.label_review import router as label_review_router
from backend_api.app.routes.me import router as me_router
from backend_api.app.routes.products import router as products_router
from backend_api.app.routes.qa import router as qa_router
from backend_api.app.routes.quota import router as quota_router
from backend_api.app.routes.scrape import router as scrape_router
from backend_api.app.routes.settings import router as settings_router
from backend_api.app.routes.taxonomy import router as taxonomy_router
from backend_api.app.routes.translate import router as translate_router
from backend_api.app.routes.unsubscribe import router as unsubscribe_router
from backend_api.app.routes.uploads import router as uploads_router
from backend_api.app.routes.workspace import router as workspace_router
from backend_api.app.services.label_registry_frontstage import (
    label_registry_shadow_middleware,
)

settings = get_settings()


def _get_cors_origins() -> list[str]:
    defaults = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3100",
    ]
    raw = os.getenv("API_CORS_ORIGINS", "")
    for origin in raw.split(","):
        candidate = origin.strip()
        if candidate:
            defaults.append(candidate)
    return list(dict.fromkeys(defaults))

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GeoBlockMiddleware)
app.add_middleware(AnalyticsMiddleware)

# 5.9.6-D repair batch 1b: shadow → audit persistence.
# Activated only when LABEL_REGISTRY_FRONTSTAGE_MODE is shadow/enforce.
# Audit DB writes are gated by LABEL_REGISTRY_AUDIT_PERSIST (default off).
app.middleware("http")(label_registry_shadow_middleware)

logger = logging.getLogger(__name__)

# 5.9.6-D repair batch 0 (0-3): taxonomy index self-check.
# Must run at startup — _load_taxonomy_aspect_index is lru_cached, so a
# transient failure on first access would be pinned for the process lifetime.
# Logged rather than raised: a taxonomy problem must not take down auth,
# uploads and billing with it. The status is surfaced on /health so the failure
# is visible instead of silent.
_taxonomy_health: dict[str, object] = {"status": "unknown", "detail": ""}


@app.on_event("startup")
def _check_taxonomy_index_health() -> None:
    from backend_api.app.services.review_fragment_label_catalog import (
        TaxonomyIndexUnhealthy,
        assert_taxonomy_index_healthy,
    )

    try:
        count = assert_taxonomy_index_healthy()
    except TaxonomyIndexUnhealthy as exc:
        _taxonomy_health["status"] = "unhealthy"
        _taxonomy_health["detail"] = str(exc)
        logger.error(
            "STARTUP CHECK FAILED: taxonomy index unhealthy — formal labels "
            "will be rejected with scope_unavailable. %s",
            exc,
        )
    except Exception as exc:  # noqa: BLE001 - startup must not crash the app
        _taxonomy_health["status"] = "error"
        _taxonomy_health["detail"] = str(exc)
        logger.exception("STARTUP CHECK ERRORED: taxonomy index check failed")
    else:
        _taxonomy_health["status"] = "healthy"
        _taxonomy_health["detail"] = f"{count} sub_categories"


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "backend_api",
        "taxonomy_index": str(_taxonomy_health["status"]),
        "taxonomy_index_detail": str(_taxonomy_health["detail"]),
    }


app.include_router(auth_router)
app.include_router(me_router)
app.include_router(workspace_router)
app.include_router(products_router)
app.include_router(uploads_router)
app.include_router(analysis_router)
app.include_router(compare_router)
app.include_router(actions_router)
app.include_router(trackers_router)
app.include_router(qa_router)
app.include_router(quota_router)
app.include_router(scrape_router)
app.include_router(settings_router)
app.include_router(taxonomy_router)
app.include_router(calibration_router)
app.include_router(analytics_router)
app.include_router(feedback_router)
app.include_router(golden_set_router)
app.include_router(label_review_router)
app.include_router(asin_watchlist_router)
app.include_router(copywriter_router)
app.include_router(downloads_router)
app.include_router(export_router)
app.include_router(translate_router)
app.include_router(unsubscribe_router)
app.include_router(admin_router)
