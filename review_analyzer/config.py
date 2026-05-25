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

# 标签归一化映射：标准词 → 可能的变体（中英文、同义词、AI 常见误写）
# 用于把 AI 自由输出的 tag 统一到标准词，避免"包装破损"和"packaging damage"被算作两个标签
TAG_NORMALIZE_MAP: dict[str, list[str]] = {
    # ── 通用差评 ──
    "包装破损": [
        "包装损坏", "外包装破损", "包装碎了", "盒子压扁", "运输损坏",
        "packaging damage", "damaged packaging", "broken packaging", "damaged box",
    ],
    "做工粗糙": [
        "材质粗糙", "做工差", "工艺粗糙", "粗糙", "质量差", "做工不精",
        "poor quality", "cheap quality", "rough finish", "poor workmanship",
    ],
    "尺寸偏差": [
        "尺寸不符", "大小不对", "尺寸问题", "尺码偏差", "尺寸不准",
        "size issue", "wrong size", "size mismatch", "incorrect size",
    ],
    "颜色差异": [
        "色差", "颜色不符", "颜色偏差", "颜色不对", "色彩差异",
        "color difference", "color mismatch", "wrong color", "color variation",
    ],
    "气味刺鼻": [
        "异味", "味道大", "化学气味", "刺鼻气味", "气味难闻", "有异味",
        "bad smell", "chemical smell", "strong odor", "unpleasant smell",
    ],
    "安装困难": [
        "难安装", "安装复杂", "安装麻烦", "组装困难", "安装不易", "组装麻烦",
        "difficult to assemble", "hard to assemble", "assembly issue", "assembly difficult",
    ],
    "稳定性差": [
        "不稳", "摇晃", "松动", "不稳固", "晃动",
        "unstable", "wobbly", "shaky", "not sturdy",
    ],
    "功能失效": [
        "功能故障", "功能不正常", "不能用", "坏了", "失灵",
        "not working", "broken", "malfunction", "defective", "doesn't work",
    ],
    "材质安全问题": [
        "材质有问题", "安全问题", "有害材质", "不安全",
        "safety issue", "material safety", "harmful material",
    ],
    "耐用性差": [
        "不耐用", "容易坏", "质量不行", "寿命短",
        "not durable", "broke easily", "poor durability", "falls apart",
    ],
    "充电问题": [
        "充电慢", "充不进去", "充电异常", "充电故障",
        "charging issue", "won't charge", "slow charging", "charging problem",
    ],
    "续航短": [
        "电池不耐用", "电量少", "续航不行",
        "short battery life", "poor battery", "battery drains fast",
    ],
    "连接不稳定": [
        "连接断开", "信号差", "掉线", "连接问题",
        "connection issue", "unstable connection", "keeps disconnecting",
    ],
    "发热严重": [
        "发烫", "过热", "温度高",
        "overheating", "gets hot", "too hot",
    ],
    "音质差": [
        "声音差", "音效差", "杂音多",
        "poor sound quality", "bad audio", "sound issue",
    ],
    "面料差": [
        "布料差", "材质差", "质感差",
        "poor fabric", "cheap fabric", "bad material",
    ],
    "缩水变形": [
        "变形", "缩水", "洗后变形",
        "shrinks", "deformed", "warped after washing",
    ],
    "掉色": [
        "褪色", "掉染料",
        "color fading", "fades", "bleeds color",
    ],
    "过敏反应": [
        "皮肤过敏", "刺激皮肤", "引起过敏",
        "allergic reaction", "skin irritation", "causes allergy",
    ],
    "效果不明显": [
        "没效果", "效果差", "效果不好",
        "doesn't work", "no effect", "ineffective",
    ],
    "清洁困难": [
        "不好清洗", "难清洁", "清洗麻烦",
        "hard to clean", "difficult to clean", "cleaning issue",
    ],
    "防水失效": [
        "不防水", "进水", "防水不好",
        "not waterproof", "water leaks", "waterproofing failed",
    ],
    "重量偏重": [
        "太重", "偏重",
        "too heavy", "heavy", "overweight",
    ],
    "性价比低": [
        "不值这个价", "价格偏高", "太贵", "性价比差",
        "overpriced", "not worth it", "too expensive", "poor value",
    ],
    # ── 通用好评 ──
    "性价比高": [
        "性价比好", "实惠", "值这个价", "划算",
        "great value", "value for money", "worth it", "affordable",
    ],
    "做工精细": [
        "做工好", "工艺好", "做工扎实", "精工细作",
        "great quality", "well made", "good craftsmanship", "high quality",
    ],
    "安装简单": [
        "安装方便", "好安装", "组装方便",
        "easy to assemble", "easy assembly", "simple installation",
    ],
    "外观好看": [
        "外观漂亮", "颜值高", "好看", "美观",
        "looks great", "beautiful", "nice looking", "attractive",
    ],
    "材质扎实": [
        "材质好", "结实", "扎实",
        "sturdy", "solid", "durable material", "good material",
    ],
    "使用方便": [
        "方便使用", "好用", "操作简单",
        "easy to use", "convenient", "user friendly",
    ],
    "效果显著": [
        "效果好", "效果明显", "很有效",
        "works great", "effective", "great results",
    ],
    "耐用性强": [
        "耐用", "结实耐用", "经久耐用",
        "durable", "long lasting", "very durable",
    ],
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
