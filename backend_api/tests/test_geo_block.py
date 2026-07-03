"""GeoBlockMiddleware 单元测试.

使用最小 FastAPI 应用装载 middleware,避免触发真实 /auth/register 的数据库操作.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend_api.app.middleware.geo_block import (
    BLOCKED_COUNTRIES,
    GeoBlockMiddleware,
)


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(GeoBlockMiddleware)

    @app.post("/auth/register")
    def register_stub() -> dict:
        return {"ok": True}

    @app.post("/auth/login")
    def login_stub() -> dict:
        return {"ok": True}

    @app.get("/health")
    def health_stub() -> dict:
        return {"status": "ok"}

    return app


def test_blocked_eu_country_returns_403():
    client = TestClient(_make_app())
    resp = client.post("/auth/register", headers={"CF-IPCountry": "DE"}, json={})
    assert resp.status_code == 403
    body = resp.json()
    assert body["reason"] == "geo_blocked"
    assert body["country"] == "DE"


def test_blocked_ofac_country_returns_403():
    client = TestClient(_make_app())
    resp = client.post("/auth/register", headers={"CF-IPCountry": "IR"}, json={})
    assert resp.status_code == 403
    assert resp.json()["country"] == "IR"


def test_missing_cf_ipcountry_header_allows_through():
    client = TestClient(_make_app())
    resp = client.post("/auth/register", json={})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_allowed_country_passes():
    client = TestClient(_make_app())
    resp = client.post("/auth/register", headers={"CF-IPCountry": "US"}, json={})
    assert resp.status_code == 200


def test_case_insensitive_country_code():
    client = TestClient(_make_app())
    resp = client.post("/auth/register", headers={"CF-IPCountry": "de"}, json={})
    assert resp.status_code == 403


def test_non_register_path_never_blocked():
    client = TestClient(_make_app())
    # 登录端点即使来自受限国家也应放行(存量用户不受影响)
    resp = client.post("/auth/login", headers={"CF-IPCountry": "DE"}, json={})
    assert resp.status_code == 200

    # 其他 GET 请求也不拦
    resp = client.get("/health", headers={"CF-IPCountry": "IR"})
    assert resp.status_code == 200


def test_get_register_path_not_blocked():
    # 只拦 POST /auth/register,GET 同路径(理论上不存在)不拦
    app = FastAPI()
    app.add_middleware(GeoBlockMiddleware)

    @app.get("/auth/register")
    def get_stub() -> dict:
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/auth/register", headers={"CF-IPCountry": "DE"})
    assert resp.status_code == 200


def test_blocked_countries_list_composition():
    # EU 27 抽样
    for cc in ("DE", "FR", "IT", "ES", "PL"):
        assert cc in BLOCKED_COUNTRIES
    # EEA 3
    for cc in ("IS", "LI", "NO"):
        assert cc in BLOCKED_COUNTRIES
    # UK + CH
    for cc in ("GB", "CH"):
        assert cc in BLOCKED_COUNTRIES
    # OFAC 6
    for cc in ("IR", "KP", "SY", "CU", "RU", "BY"):
        assert cc in BLOCKED_COUNTRIES
    # 未拦国家抽样
    for cc in ("US", "CA", "JP", "AU", "SG", "CN"):
        assert cc not in BLOCKED_COUNTRIES
    # 总数校验: 27 + 3 + 2 + 6 = 38
    assert len(BLOCKED_COUNTRIES) == 38
