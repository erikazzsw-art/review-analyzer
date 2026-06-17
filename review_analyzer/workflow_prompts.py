from __future__ import annotations

WORKFLOW_PURPOSES = [
    "竞品调研",
    "新品上线监控",
    "日常评论分析",
    "Listing 优化",
    "质量问题复盘",
    "版本改版验证",
]


WORKFLOW_PURPOSE_HINTS = {
    "竞品调研": "更适合关注必备功能、加分功能、无效功能和产品机会点。",
    "新品上线监控": "更适合关注首批差评、误用场景、新增卖点是否被用户感知。",
    "日常评论分析": "更适合做常规问题监控、亮点提炼和趋势观察。",
    "Listing 优化": "更适合优先识别使用误解、描述不清和卖点表达不足。",
    "质量问题复盘": "更适合围绕同一问题持续追踪，判断改进后是否真的下降。",
    "版本改版验证": "更适合把当前结果放到版本对比和卖点验证里解读。",
}


WORKFLOW_RESULT_FOCUS = {
    "竞品调研": "建议优先查看 TOP 问题、TOP 亮点和代表性原文，整理竞品短板与机会点。",
    "新品上线监控": "建议优先查看高频差评和新增问题，判断是否存在早期质量或场景误解风险。",
    "日常评论分析": "建议结合时间筛选和 Ask your reviews 做常规监控与主题追问。",
    "Listing 优化": "建议重点关注误用、描述不符、安装说明不清等问题，并转成运营动作。",
    "质量问题复盘": "建议重点关注问题占比是否下降，这批评论后续可直接衔接复盘追踪。",
    "版本改版验证": "建议优先查看版本对比区域，判断改版功能是否真的被用户认可。",
}


COMPARISON_TYPE_FOCUS = {
    "same_product_time": "适合判断同一产品的问题是在改善、持平还是恶化，重点看差评率和 TOP 问题变化。",
    "same_product_version": "适合验证版本改版是否生效，重点看新增亮点是否被感知、旧问题是否下降。",
    "same_parent_variants": "适合同父体下找出高风险变体和主推变体，重点看不同 SKU 的问题结构差异。",
    "multi_product": "适合横向判断主推款、机会款和风险款，重点看差评率、亮点密度和代表性问题。",
    "custom": "适合按批次自由组合验证你的业务假设，重点看每组范围是否一致、结论是否可执行。",
}

WORKFLOW_PURPOSE_LABELS = {
    "竞品调研": {"zh": "竞品调研", "en": "Competitor Research"},
    "新品上线监控": {"zh": "新品上线监控", "en": "New Launch Monitoring"},
    "日常评论分析": {"zh": "日常评论分析", "en": "Routine Review Analysis"},
    "Listing 优化": {"zh": "Listing 优化", "en": "Listing Optimization"},
    "质量问题复盘": {"zh": "质量问题复盘", "en": "Quality Issue Follow-up"},
    "版本改版验证": {"zh": "版本改版验证", "en": "Version Update Validation"},
}

WORKFLOW_PURPOSE_HINTS_EN = {
    "竞品调研": "Best for identifying must-have features, bonus features, nonessential features, and product opportunity gaps.",
    "新品上线监控": "Best for tracking early negative feedback, misuse scenarios, and whether new selling points are being noticed.",
    "日常评论分析": "Best for routine issue monitoring, highlight extraction, and trend tracking.",
    "Listing 优化": "Best for identifying usage misunderstandings, unclear descriptions, and weak selling-point messaging first.",
    "质量问题复盘": "Best for tracking the same issue over time and validating whether it really declines after improvements.",
    "版本改版验证": "Best for reading the current batch through version comparison and selling-point validation.",
}

WORKFLOW_RESULT_FOCUS_EN = {
    "竞品调研": "Start with top issues, top highlights, and representative quotes to summarize competitor weaknesses and opportunity areas.",
    "新品上线监控": "Start with recurring negative feedback and newly emerging issues to judge early quality or scenario-mismatch risk.",
    "日常评论分析": "Use the time filter together with Review Q&A for routine monitoring and deeper follow-up questions.",
    "Listing 优化": "Focus on misuse, description mismatch, and unclear setup guidance, then turn them into operations actions.",
    "质量问题复盘": "Focus on whether the issue share is actually falling. This batch can connect directly to follow-up tracking.",
    "版本改版验证": "Start with the version comparison section to judge whether the updated features are truly being recognized.",
}

COMPARISON_TYPE_FOCUS_EN = {
    "same_product_time": "Best for judging whether issues in the same product are improving, flat, or worsening. Focus on negative rate and top-issue changes.",
    "same_product_version": "Best for validating whether a version update worked. Focus on whether new highlights are noticed and old issues decline.",
    "same_parent_variants": "Best for finding high-risk variants and priority variants within the same parent product. Focus on issue-structure differences across SKUs.",
    "multi_product": "Best for comparing priority products, opportunity products, and risk products side by side. Focus on negative rate, highlight density, and representative issues.",
    "custom": "Best for validating your own business hypothesis by combining custom batches. Focus on consistent scope and actionable conclusions.",
}


def _pick_text(mapping_zh: dict[str, str], mapping_en: dict[str, str], key: str, lang: str | None = None) -> str | None:
    selected_lang = lang or "zh"
    if selected_lang == "en":
        return mapping_en.get(key)
    return mapping_zh.get(key)


def get_workflow_purpose_label(purpose: str | None, lang: str | None = None) -> str:
    if not purpose:
        return ""
    selected_lang = lang or "zh"
    label_mapping = WORKFLOW_PURPOSE_LABELS.get(purpose)
    if not label_mapping:
        return purpose
    return label_mapping.get(selected_lang, label_mapping["zh"])


def get_workflow_hint(purpose: str | None) -> str | None:
    if not purpose:
        return None
    return _pick_text(WORKFLOW_PURPOSE_HINTS, WORKFLOW_PURPOSE_HINTS_EN, purpose)


def get_result_focus_hint(purpose: str | None) -> str | None:
    if not purpose:
        return None
    return _pick_text(WORKFLOW_RESULT_FOCUS, WORKFLOW_RESULT_FOCUS_EN, purpose)


def get_comparison_focus_hint(compare_type: str | None) -> str | None:
    if not compare_type:
        return None
    return _pick_text(COMPARISON_TYPE_FOCUS, COMPARISON_TYPE_FOCUS_EN, compare_type)
