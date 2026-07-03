"""Geo-block middleware for EU/UK/EEA + OFAC-sanctioned countries.

Only intercepts POST /auth/register to avoid impacting existing users on other endpoints.
Country code is read from Cloudflare's ``CF-IPCountry`` request header. When the header
is absent (e.g. Cloudflare not yet fronting traffic during rollout), the request is
allowed through with a DEBUG log — we deliberately do not hard-fail, so that switching
Cloudflare on/off does not lock legitimate users out.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


# EU 27 成员国
_EU_27 = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
})

# EEA 非 EU（冰岛 / 列支敦士登 / 挪威）
_EEA_NON_EU = frozenset({"IS", "LI", "NO"})

# 英国 + 瑞士（同属欧洲合规范围但非 EU/EEA）
_UK_CH = frozenset({"GB", "CH"})

# OFAC 全面制裁国（清单以最新 OFAC 公告为准）：伊朗、朝鲜、叙利亚、古巴、俄罗斯、白俄罗斯
_OFAC_SANCTIONED = frozenset({"IR", "KP", "SY", "CU", "RU", "BY"})

BLOCKED_COUNTRIES: frozenset[str] = _EU_27 | _EEA_NON_EU | _UK_CH | _OFAC_SANCTIONED


BLOCKED_ENDPOINTS: frozenset[tuple[str, str]] = frozenset({
    ("POST", "/auth/register"),
})


class GeoBlockMiddleware(BaseHTTPMiddleware):
    """拦截来自受限国家的注册请求。

    - 只匹配 ``BLOCKED_ENDPOINTS`` 中的 (method, path) 组合，其他请求全部放行
    - ``CF-IPCountry`` 缺失 → 放行 + DEBUG 日志（Cloudflare 未上线阶段的兜底）
    - 命中受限国家 → 返回 403 JSON，明确告知合规原因
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if (request.method, request.url.path) not in BLOCKED_ENDPOINTS:
            return await call_next(request)

        country = (request.headers.get("CF-IPCountry") or "").strip().upper()
        if not country:
            logger.debug(
                "geo_block: CF-IPCountry missing on %s %s; allowing through",
                request.method, request.url.path,
            )
            return await call_next(request)

        if country in BLOCKED_COUNTRIES:
            logger.info(
                "geo_block: blocked %s %s from country=%s",
                request.method, request.url.path, country,
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        "Registration is not available in your region due to "
                        "regulatory compliance requirements."
                    ),
                    "country": country,
                    "reason": "geo_blocked",
                },
            )

        return await call_next(request)
