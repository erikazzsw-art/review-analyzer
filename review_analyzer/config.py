"""类目预设标签库配置"""

from __future__ import annotations

from typing import TypedDict


class CategoryTags(TypedDict):
    negative: list[str]
    positive: list[str]


CATEGORY_TAGS: dict[str, CategoryTags] = {
    "家具家居": {
        "negative": [
            "包装破损", "安装困难", "材质粗糙", "尺寸偏差",
            "颜色差异", "气味刺鼻", "稳定性差",
        ],
        "positive": [
            "做工精细", "安装简单", "外观好看", "材质扎实", "性价比高",
        ],
    },
    "3C电子": {
        "negative": [
            "充电问题", "续航短", "连接不稳定", "功能失效",
            "发热严重", "音质差",
        ],
        "positive": [
            "音质出色", "续航强", "连接稳定", "功能丰富", "响应快",
        ],
    },
    "服装鞋帽": {
        "negative": [
            "尺码偏差", "颜色差异", "做工粗糙", "面料差",
            "缩水变形", "掉色",
        ],
        "positive": [
            "版型好看", "面料舒适", "做工精细", "颜色正", "尺码准确",
        ],
    },
    "母婴用品": {
        "negative": [
            "材质安全问题", "尺寸偏差", "做工粗糙", "气味刺鼻", "功能失效",
        ],
        "positive": [
            "材质安全", "做工精细", "宝宝喜欢", "使用方便", "性价比高",
        ],
    },
    "运动户外": {
        "negative": [
            "耐用性差", "尺码偏差", "防水失效", "做工粗糙", "重量偏重",
        ],
        "positive": [
            "耐用性强", "轻便舒适", "防水效果好", "外观好看", "性价比高",
        ],
    },
    "美妆个护": {
        "negative": [
            "气味刺鼻", "过敏反应", "效果不明显", "包装破损", "成分问题",
        ],
        "positive": [
            "效果显著", "气味好闻", "质地舒适", "包装精美", "性价比高",
        ],
    },
    "厨房用品": {
        "negative": [
            "材质安全问题", "做工粗糙", "尺寸偏差", "功能失效", "清洁困难",
        ],
        "positive": [
            "使用方便", "做工精细", "材质安全", "清洁简单", "性价比高",
        ],
    },
    "宠物用品": {
        "negative": [
            "材质安全问题", "尺寸偏差", "做工粗糙", "气味刺鼻", "耐用性差",
        ],
        "positive": [
            "宠物喜欢", "材质安全", "做工精细", "使用方便", "性价比高",
        ],
    },
}

DEFAULT_CATEGORY: str = "家具家居"

CATEGORY_LIST: list[str] = list(CATEGORY_TAGS.keys())

VERSION_OPTIONS: list[str] = [f"V{i}" for i in range(1, 101)]

SENTIMENT_LABELS: list[str] = ["positive", "negative", "neutral", "unrecognizable"]

PRIORITY_LABELS: list[str] = ["高", "中", "低", "无"]

CATEGORY_LABELS: list[str] = [
    "功能建议", "Bug报告", "体验问题", "隐私担忧",
    "询问", "有价值正面反馈", "单纯好评", "无效乱码", "其他",
]

CONTENT_COLUMN_ALIASES: list[str] = [
    "content", "review", "review_text", "评论", "评论内容", "内容", "comment", "text",
]

DATE_COLUMN_ALIASES: list[str] = [
    "date", "review_date", "time", "日期", "时间", "评论时间", "评论日期",
]

RATING_COLUMN_ALIASES: list[str] = [
    "rating", "stars", "score", "评分", "星级", "分数",
]

USER_COLUMN_ALIASES: list[str] = [
    "user_id", "reviewer", "username", "用户", "用户ID", "昵称",
]

SOURCE_COLUMN_ALIASES: list[str] = [
    "source", "platform", "channel", "渠道", "来源", "平台",
]
