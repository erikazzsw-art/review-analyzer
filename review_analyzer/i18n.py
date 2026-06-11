from __future__ import annotations

from typing import Any

import streamlit as st

DEFAULT_LANG = "zh"
SUPPORTED_LANGS = {"zh", "en"}


NAV_ITEMS = {
    "zh": {
        "dashboard": ("📊", "今日工作台"),
        "products": ("🗂️", "产品管理"),
        "upload": ("📤", "上传评论"),
        "analysis": ("🔎", "评论分析"),
        "rag": ("💬", "问评论"),
        "actions": ("✅", "行动中心"),
        "reviews": ("🔁", "复盘追踪"),
        "copywriter": ("✍️", "宣传文案"),
        "settings": ("⚙️", "推送设置"),
    },
    "en": {
        "dashboard": ("📊", "Today's Workspace"),
        "products": ("🗂️", "Product Management"),
        "upload": ("📤", "Upload Reviews"),
        "analysis": ("🔎", "Review Analysis"),
        "rag": ("💬", "Review Q&A"),
        "actions": ("✅", "Action Center"),
        "reviews": ("🔁", "Follow-up Tracking"),
        "copywriter": ("✍️", "Marketing Copy"),
        "settings": ("⚙️", "Notification Settings"),
    },
}


COMMON_TEXT = {
    "zh": {
        "app_title": "ClueAI - 评论分析系统",
        "brand_button": "ClueAI",
        "logout": "退出登录",
        "preview_landing": "预览当前欢迎页",
        "preview_landing_new": "预览新版欢迎页",
        "back_to_workspace": "返回工作台",
        "login_required": "请先登录",
        "continue_reading": "继续往下看",
        "language_zh": "中文",
        "language_en": "EN",
    },
    "en": {
        "app_title": "ClueAI - Review Analysis System",
        "brand_button": "ClueAI",
        "logout": "Logout",
        "preview_landing": "Preview Current Landing",
        "preview_landing_new": "Preview New Landing",
        "back_to_workspace": "Back to Workspace",
        "login_required": "Please log in first.",
        "continue_reading": "Continue below",
        "language_zh": "中文",
        "language_en": "EN",
    },
}

ROLE_LABELS = {
    "运营": {"zh": "运营", "en": "Operations"},
    "产研": {"zh": "产研", "en": "Product & R&D"},
    "质检": {"zh": "质检", "en": "Quality Assurance"},
    "管理者": {"zh": "管理者", "en": "Manager"},
    "复盘": {"zh": "复盘", "en": "Follow-up"},
    "跨团队": {"zh": "跨团队", "en": "Cross-functional"},
}

ACTION_STATUS_LABELS_I18N = {
    "todo": {"zh": "待处理", "en": "To Do"},
    "in_progress": {"zh": "处理中", "en": "In Progress"},
    "pending_review": {"zh": "待复盘", "en": "Pending Follow-up"},
    "done": {"zh": "已完结", "en": "Done"},
}

TRACKER_STATUS_LABELS_I18N = {
    "pending": {"zh": "待复盘", "en": "Pending Follow-up"},
    "improved": {"zh": "已改善", "en": "Improved"},
    "not_improved": {"zh": "未改善", "en": "Not Improved"},
    "follow_up": {"zh": "继续跟进", "en": "Continue Tracking"},
    "done": {"zh": "已完结", "en": "Done"},
}


def get_lang() -> str:
    raw_lang = str(st.session_state.get("lang", DEFAULT_LANG))
    if raw_lang not in SUPPORTED_LANGS:
        raw_lang = DEFAULT_LANG
        st.session_state["lang"] = raw_lang
    return raw_lang


def set_lang(lang: str) -> None:
    st.session_state["lang"] = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG


def t(key: str) -> str:
    lang = get_lang()
    return COMMON_TEXT.get(lang, COMMON_TEXT[DEFAULT_LANG]).get(key, key)


def pick(zh: Any, en: Any) -> Any:
    return zh if get_lang() == "zh" else en


def nav_items() -> dict[str, tuple[str, str]]:
    return NAV_ITEMS[get_lang()]


def role_label(value: str | None) -> str:
    if not value:
        return pick("未分配", "Unassigned")
    mapping = ROLE_LABELS.get(value)
    if not mapping:
        return value
    return mapping.get(get_lang(), mapping["zh"])


def action_status_label(value: str | None) -> str:
    if not value:
        return pick("—", "—")
    mapping = ACTION_STATUS_LABELS_I18N.get(value)
    if not mapping:
        return value
    return mapping.get(get_lang(), mapping["zh"])


def tracker_status_label(value: str | None) -> str:
    if not value:
        return pick("—", "—")
    mapping = TRACKER_STATUS_LABELS_I18N.get(value)
    if not mapping:
        return value
    return mapping.get(get_lang(), mapping["zh"])
