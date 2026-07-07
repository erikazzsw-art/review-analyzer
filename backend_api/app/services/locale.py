"""LLM 分析 locale 检测（决定走哪条模型链）.

优先级：
1. 查询参数 `?locale=xx`（显式覆盖，测试/调试用）
2. Cookie `NEXT_LOCALE`（前端 next-intl 写入）
3. 请求头 `Accept-Language`（浏览器兜底）
4. 默认 "en"（海外优先）

只区分 "en" / "zh" 两条链，其它值统一按 "en" 处理，因为海外用户占大多数。
"""
from __future__ import annotations

from fastapi import Request

DEFAULT_ANALYSIS_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "zh")


def _normalize(raw: str | None) -> str | None:
    if not raw:
        return None
    lower = raw.strip().lower()
    if not lower:
        return None
    # 拆掉 region：zh-CN → zh, en-US → en
    primary = lower.split(",")[0].split("-")[0].split("_")[0].strip()
    if primary in SUPPORTED_LOCALES:
        return primary
    if primary.startswith("zh"):
        return "zh"
    if primary.startswith("en"):
        return "en"
    return None


def get_analysis_locale(request: Request) -> str:
    """从请求推断 LLM 分析用 locale。

    永远返回 "en" 或 "zh"，不抛异常。
    """
    # 1. query param
    qp = _normalize(request.query_params.get("locale"))
    if qp:
        return qp

    # 2. cookie
    cookie = _normalize(request.cookies.get("NEXT_LOCALE"))
    if cookie:
        return cookie

    # 3. Accept-Language
    header = _normalize(request.headers.get("accept-language"))
    if header:
        return header

    return DEFAULT_ANALYSIS_LOCALE
