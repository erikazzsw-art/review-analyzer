from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend_api.app.config import get_settings
from backend_api.app.routes.auth import router as auth_router
from backend_api.app.routes.analysis import router as analysis_router
from backend_api.app.routes.actions import router as actions_router
from backend_api.app.routes.actions import trackers_router as trackers_router
from backend_api.app.routes.compare import router as compare_router
from backend_api.app.routes.me import router as me_router
from backend_api.app.routes.products import router as products_router
from backend_api.app.routes.qa import router as qa_router
from backend_api.app.routes.settings import router as settings_router
from backend_api.app.routes.taxonomy import router as taxonomy_router
from backend_api.app.routes.quota import router as quota_router
from backend_api.app.routes.uploads import router as uploads_router
from backend_api.app.routes.workspace import router as workspace_router


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend_api"}


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
app.include_router(settings_router)
app.include_router(taxonomy_router)
