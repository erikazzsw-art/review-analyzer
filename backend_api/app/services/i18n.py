"""Backend i18n 服务层 — 用户 UI 语言检测.

优先级：
1. Cookie `NEXT_LOCALE`（前端 next-intl 写入，最可靠）
2. 请求头 `Accept-Language`（浏览器兜底）
3. 默认 "en-US"（海外优先）

与 `services/locale.py` 的区别：
- `locale.py` 返回 "en"/"zh"，用于 LLM 分析链路由（M4-pre）
- `i18n.py` 返回完整 locale tag（"en-US"/"zh-CN"），用于邮件模板选择 / 后端文案
"""
from __future__ import annotations

from fastapi import Request

DEFAULT_UI_LOCALE = "en-US"

# 后端当前支持的 UI 语言（与前端 next-intl 的 locales 配置对齐）
SUPPORTED_UI_LOCALES = frozenset({"en-US", "zh-CN"})

# Accept-Language → 归一化 locale 的映射（取首个匹配的语言标签）
# 只映射到后端支持的 locale，不支持的返回 None（走默认值）
_NORMALIZE_MAP: dict[str, str] = {
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-hans": "zh-CN",
    "zh-hant": "zh-CN",
    "zh-tw": "zh-CN",
    "zh-hk": "zh-CN",
    "en": "en-US",
    "en-us": "en-US",
    "en-gb": "en-US",
    "en-ca": "en-US",
    "en-au": "en-US",
}


def normalize_locale(raw: str | None) -> str | None:
    """将任意 locale 字符串归一化为后端支持的 locale tag.

    Returns:
        归一化后的 locale（"en-US" / "zh-CN"），不支持则返回 None
    """
    if not raw:
        return None
    lower = raw.strip().lower()
    if not lower:
        return None

    # 精确匹配
    if lower in _NORMALIZE_MAP:
        return _NORMALIZE_MAP[lower]

    # 取主语言标签（zh-CN → zh）
    primary = lower.split(",")[0].split("-")[0].split("_")[0].strip()
    if primary in _NORMALIZE_MAP:
        return _NORMALIZE_MAP[primary]

    return None


def get_user_locale(request: Request) -> str:
    """从请求推断用户 UI 语言偏好.

    永远返回有效的 locale tag（"en-US" 或 "zh-CN"），不抛异常.
    """
    # 1. Cookie（前端 next-intl 写入，最可靠）
    cookie = normalize_locale(request.cookies.get("NEXT_LOCALE"))
    if cookie:
        return cookie

    # 2. Accept-Language header（浏览器兜底）
    header = normalize_locale(request.headers.get("accept-language"))
    if header:
        return header

    # 3. 默认
    return DEFAULT_UI_LOCALE
