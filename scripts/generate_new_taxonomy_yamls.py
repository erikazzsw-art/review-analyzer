"""批量生成新品类 taxonomy YAML 文件.

运行方式: python3 scripts/generate_new_taxonomy_yamls.py
"""
from __future__ import annotations

import textwrap
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent / "data" / "taxonomy" / "v1.0"

# ── 通用 base aspects ──────────────────────────────────────────────────────────
# 各品类的 base aspects 携带品类特定的 boundary_note
# key → (label_zh, boundary_note)
BASE_ASPECTS: list[tuple[str, str, str]] = [
    ("build_quality", "做工", "制造工艺、做工细节（缝合/拉链/接缝），不含材质本身"),
    ("durability", "耐用性", "长期使用后的耐磨损表现，不含到货损坏（归 shipping_damage）"),
    ("material", "材质用料", "面料/材质手感、厚薄质感，不含功能性（功能归各专项）"),
    ("ease_of_use", "易用性", "日常操作便捷性，不含安装过程（有专项时归安装 aspect）"),
    ("aesthetics", "外观设计", "颜色、款式、外观好看程度"),
    ("packaging", "包装", "外包装质量和美观度，不含运输损坏"),
    ("shipping_damage", "运输损坏", "到货时损坏或缺件，不含产品本身质量问题"),
    ("customer_service", "客服", "售后服务、退换货体验"),
    ("value_for_money", "性价比", "价格与整体品质的匹配感"),
    ("other", "其他", "不属于以上任何维度的评论内容（兜底）"),
]


def _aspect_block(key: str, label_zh: str, boundary_note: str) -> str:
    return textwrap.dedent(f"""\
  - key: {key}
    label_zh: {label_zh}
    total: 0
    positive_count: 0
    negative_count: 0
    neutral_count: 0
    negative_rate: 0.0%
    boundary_note: "{boundary_note}"
    top_phrases: []
    sample_reviews: []
""")


def write_yaml(
    category: str,
    sub_category: str,
    delta_aspects: list[tuple[str, str, str]],
    base_overrides: dict[str, tuple[str, str]] | None = None,
) -> None:
    """生成单个子品类 YAML 文件."""
    out_dir = BASE_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{sub_category}.yaml"

    all_aspects: list[tuple[str, str, str]] = []
    base_override_map = base_overrides or {}

    # 先加 delta aspects（产品特有维度）
    for key, label, note in delta_aspects:
        all_aspects.append((key, label, note))

    # 再加 base aspects（通用维度，可被 override）
    for key, label, note in BASE_ASPECTS:
        if key == "other":
            continue  # other 固定放最后
        if key in base_override_map:
            label, note = base_override_map[key]
        all_aspects.append((key, label, note))

    all_aspects.append(("other", "其他", "不属于以上任何维度的评论内容（兜底）"))

    lines = [
        f"# {sub_category} Aspect Taxonomy v1.0",
        "# 生成时间: 2026-06-30 (手动生成，参考跨境电商评论维度)",
        f"sub_category: {sub_category}",
        f"aspect_count: {len(all_aspects)}",
        "aspects:",
    ]
    for key, label, note in all_aspects:
        lines.append(_aspect_block(key, label, note))

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ {category}/{sub_category}.yaml ({len(all_aspects)} aspects)")


# ── OUTDOOR 品类 ───────────────────────────────────────────────────────────────
OUTDOOR = {
    "登山鞋": [
        ("waterproof", "防水性", "鞋内是否进水渗湿，仅限防水，不含透气（透气归 breathability）"),
        ("breathability", "透气性", "长时间行走是否闷热出汗，不含防水"),
        ("grip", "抓地力", "鞋底在泥土/岩石等户外地面的抓地防滑效果"),
        ("ankle_support", "踝部支撑", "脚踝稳定支撑保护，防扭伤效果"),
        ("size_fit", "尺寸合脚性", "鞋码是否符合标注，鞋型是否匹配脚型"),
        ("comfort", "穿着舒适度", "长距离行走脚感舒适，不含磨脚（磨脚归 break_in）"),
        ("break_in", "磨脚/磨合期", "新鞋穿用初期是否磨脚、需要磨合期的长短"),
        ("weight", "重量", "鞋子轻重，不含其他便携性"),
    ],
    "睡袋": [
        ("temperature_rating", "保暖等级", "在对应温标下实际保暖效果，不含透气（透气归 breathability）"),
        ("breathability", "透气排湿", "睡眠中是否闷热出汗，不含保暖"),
        ("portability", "压缩便携性", "压缩后体积大小和重量，不含保暖"),
        ("zipper_quality", "拉链顺滑度", "拉链开合顺畅、不卡顿，不含做工整体（整体归 build_quality）"),
        ("size_fit", "尺寸适配", "适合的身高范围，宽松度是否合适"),
        ("comfort", "睡眠舒适度", "整体睡眠舒适感，含衬里柔软度"),
        ("smell", "异味", "新品是否有刺鼻化学气味，仅限气味维度"),
    ],
    "户外背包": [
        ("capacity", "容量/空间", "实际可装载容量，是否与标注升数一致"),
        ("comfort", "背负舒适度", "背带肩带贴合感、长时间背负是否压肩，不含重量（重量归 portability）"),
        ("waterproof", "防水性", "雨天主仓和外袋是否进水"),
        ("portability", "重量", "背包自重轻重，不含容量"),
        ("organization", "收纳分区", "口袋分区设计合理性、取放物品方便性"),
        ("stability", "负重稳定性", "满载时背包稳定不晃，腰带/胸带支撑效果"),
        ("size_fit", "体型适配", "背长调节范围，适合的身型"),
    ],
    "钓鱼竿": [
        ("sensitivity", "手感灵敏度", "传导鱼咬钩信号的灵敏程度"),
        ("strength", "强度/承重", "抗折、拉力测试表现，不含耐腐蚀（耐腐蚀归 corrosion_resistance）"),
        ("portability", "重量/便携", "鱼竿轻重和收纳长度"),
        ("corrosion_resistance", "耐腐蚀性", "海钓/淡水长期使用后是否生锈腐蚀"),
        ("grip_comfort", "握持手感", "手柄材质和握持舒适性"),
        ("action", "调性/弹性", "鱼竿弯曲弧度和回弹特性（硬调/中调/软调）"),
        ("assembly", "连接顺滑度", "节竿连接顺畅、不松动"),
    ],
}

for sub, delta in OUTDOOR.items():
    write_yaml("outdoor", sub, delta)

# ── BEAUTY 美妆个护 ────────────────────────────────────────────────────────────
BEAUTY = {
    "面霜": [
        ("efficacy", "保湿/修护效果", "实际保湿、美白、抗衰等护肤效果，不含质地（质地归 texture）"),
        ("skin_compatibility", "肤质适配/刺激性", "是否引发过敏、闭口、痘痘，仅限皮肤反应"),
        ("texture", "质地手感", "膏体细腻度、涂抹延展性，不含吸收速度（吸收归 absorption）"),
        ("absorption", "吸收速度", "涂抹后是否快速吸收不油腻，不含保湿效果"),
        ("scent", "气味/香味", "产品本身的气味是否好闻，不含刺激性（刺激归 skin_compatibility）"),
        ("ingredients", "成分安全", "成分表是否含有害物质、是否适合敏感肌"),
    ],
    "洗面奶": [
        ("cleansing_efficacy", "清洁效果", "去污、控油、溶妆的清洁力度"),
        ("skin_compatibility", "温和度/刺激性", "洗后皮肤是否紧绷、泛红、刺激"),
        ("texture", "泡沫/质地", "泡沫丰富度或膏体质感，不含清洁力"),
        ("moisturizing_after_wash", "洗后保湿感", "洗完不干燥、保留皮肤水分感"),
        ("scent", "气味", "产品香味是否好闻，不含刺激性"),
        ("ingredients", "成分安全", "是否含皂基、SLS等争议成分，适合敏感肌程度"),
    ],
    "防晒霜": [
        ("spf_efficacy", "防晒效果", "实际防晒、防晒黑效果，不含质地"),
        ("skin_compatibility", "皮肤适配性", "是否致痘、过敏，适合油皮/干皮/敏感肌"),
        ("texture", "油腻感/白膜", "涂后是否油腻、是否有明显白膜，不含防晒效果"),
        ("scent", "气味", "防晒霜本身气味，不含刺激性"),
        ("longevity", "持久度", "防晒效果的持续时长，是否需要频繁补涂"),
        ("ingredients", "成分安全", "物理/化学防晒成分，是否适合儿童/孕妇"),
    ],
    "口红": [
        ("color_payoff", "显色度", "颜色显色是否饱满，与色号描述是否一致"),
        ("longevity", "持久度", "口红持色时长，是否容易脱色"),
        ("texture", "质地", "涂抹滑润度、是否拔干，不含滋润效果（滋润归 moisturizing）"),
        ("moisturizing", "滋润度", "嘴唇保湿感，不含颜色（颜色归 color_payoff）"),
        ("scent", "气味", "口红本身的香味或异味"),
        ("skin_compatibility", "刺激性", "是否引发唇部过敏、蜕皮"),
    ],
    "洗发水": [
        ("cleansing_efficacy", "去污控油效果", "头发和头皮清洁力，控油持久度"),
        ("scalp_compatibility", "头皮适配/刺激性", "是否刺激头皮、引发瘙痒或脱发，适合发质类型"),
        ("scent", "香味", "洗发水和洗后头发的气味"),
        ("hair_feel_after", "洗后发质感", "洗后头发柔顺、蓬松还是干涩"),
        ("foam", "泡沫丰富度", "起泡效果是否丰富，不含清洁力"),
        ("residue", "冲洗清爽度", "冲洗是否彻底不残留，不含洗后发质"),
    ],
    "电动牙刷": [
        ("cleaning_efficacy", "清洁效果", "牙齿清洁力、去牙渍效果，不含刷头（刷头归 brush_head_quality）"),
        ("noise", "振动噪音", "使用时发出的声响，仅限噪音维度"),
        ("vibration_strength", "振动强度", "振动力度是否合适，不含噪音"),
        ("battery_life", "续航", "充满电后可使用天数"),
        ("charging", "充电方式", "充电速度和充电设计，不含续航"),
        ("brush_head_quality", "刷头质量", "刷毛柔软度、刷头耐用性，不含清洁效果"),
    ],
}

for sub, delta in BEAUTY.items():
    write_yaml("beauty", sub, delta)

# ── KITCHEN 厨房用品 ────────────────────────────────────────────────────────────
KITCHEN = {
    "不粘锅": [
        ("non_stick", "不粘性能", "食材是否粘锅，不粘涂层效果，不含清洗便捷（清洗归 cleaning）"),
        ("heat_distribution", "导热均匀性", "锅底受热是否均匀不局部焦糊"),
        ("cleaning", "清洗便捷性", "锅内壁清洗是否容易，不含不粘性能"),
        ("weight", "重量", "锅体重量轻重，不含材质"),
        ("coating_durability", "涂层耐磨性", "不粘涂层长期使用后是否脱落划伤"),
        ("size_fit", "尺寸/容量", "锅径大小是否符合炉灶，容量是否够用"),
        ("safety", "材质安全", "涂层材质是否无毒安全（PFOA-free等）"),
    ],
    "刀具套装": [
        ("sharpness", "锋利度", "切割食材时是否省力锋利，新刀开箱锋利度"),
        ("ergonomics", "握持手感", "刀柄材质和握持舒适性，防滑效果"),
        ("balance", "重心平衡", "刀身重心是否合理，切割时是否顺手"),
        ("edge_retention", "保锋性", "使用一段时间后刃口是否快速变钝"),
        ("weight", "重量", "刀具轻重，不含平衡感"),
        ("cleaning", "清洗便捷性", "是否可洗碗机清洗，清洗后是否生锈"),
        ("storage_block", "刀架/收纳", "附带刀架质量和设计，不含刀具本身"),
    ],
    "保温杯": [
        ("insulation_performance", "保温/保冷时长", "液体保持温度的实际持续时间"),
        ("seal", "密封性", "倾斜或倒置时是否漏液"),
        ("capacity", "容量", "实际容量是否与标注一致"),
        ("ease_of_use", "开盖便捷性", "盖子开合顺畅，单手操作是否方便，不含密封性"),
        ("weight", "重量", "杯身轻重，不含容量"),
        ("taste_neutrality", "无异味影响", "是否有金属味或塑料味影响饮品口感"),
        ("cleaning", "清洗便捷性", "杯内壁和杯盖的清洗是否容易"),
    ],
    "空气炸锅": [
        ("cooking_performance", "烹饪效果", "食物熟透均匀度、外脆内嫩效果"),
        ("noise", "噪音", "工作时风扇噪音大小"),
        ("capacity", "容量/篮子大小", "实际可放食材的体积，适合人数"),
        ("cleaning", "清洗便捷性", "炸篮和内壁是否好清洗，是否可拆卸"),
        ("heat_distribution", "加热均匀性", "食物受热是否均匀，不含烹饪效果整体"),
        ("temperature_control", "控温精准", "温度和时间设置是否准确，不含加热均匀"),
        ("safety", "使用安全性", "外壳是否隔热、断电保护功能"),
    ],
    "收纳盒": [
        ("seal", "密封性", "盖子是否密封严实，适用于储存食品或防尘"),
        ("capacity", "容量/大小", "实际容积和外形尺寸是否符合描述"),
        ("stackability", "堆叠设计", "多个叠放是否稳固，节省空间"),
        ("transparency", "透明度/可视性", "是否方便隔着看清内容物"),
        ("safety", "材质安全", "是否食品级材质，耐高温、无BPA"),
        ("size_fit", "尺寸适配", "是否适合目标存放空间，如冰箱格/柜子"),
    ],
}

for sub, delta in KITCHEN.items():
    write_yaml("kitchen", sub, delta)

# ── AUTOMOTIVE 汽车配件 ─────────────────────────────────────────────────────────
AUTOMOTIVE = {
    "车载充电器": [
        ("charging_speed", "充电速度", "实际充电功率，快充是否达标"),
        ("compatibility", "兼容适配性", "适配手机品牌/型号，不同接口支持"),
        ("heat", "发热情况", "长时间充电是否过热，不含充电速度"),
        ("stability", "插头稳定性", "插入点烟口是否松动、接触不良"),
        ("indicator_light", "指示灯/显示", "充电状态指示灯，不含充电速度"),
        ("size_fit", "体积/遮挡", "是否遮挡视线或周边功能按钮"),
    ],
    "行车记录仪": [
        ("image_quality", "白天画质", "日间录像清晰度，细节是否清晰"),
        ("night_vision", "夜视效果", "夜间或低光环境录像质量，与白天分开评价"),
        ("storage", "存储卡兼容", "支持的存储卡规格，循环覆盖是否稳定"),
        ("installation", "安装固定", "吸盘/固定支架安装方便度，不含稳定性"),
        ("stability", "稳固不掉落", "行驶中是否震动脱落，与安装方便度区分"),
        ("angle_coverage", "拍摄角度", "广角覆盖范围，不含画质"),
        ("loop_recording", "循环录制", "存储满后自动覆盖功能是否稳定"),
    ],
    "座椅套": [
        ("compatibility", "车型适配性", "是否与车型/座椅形状匹配，安装后是否贴合"),
        ("installation", "安装难度", "套上座椅是否方便，不含适配性"),
        ("comfort", "坐感舒适度", "座椅套材质坐上去的舒适感，不含透气"),
        ("breathability", "透气性", "夏天是否闷热不透气"),
        ("cleaning", "清洗便捷性", "是否可拆洗，污渍是否容易清除"),
        ("size_fit", "尺寸合适度", "大小是否合适，不含车型适配"),
    ],
    "遮阳挡": [
        ("uv_blocking", "遮光隔热效果", "阳光隔挡和降温效果"),
        ("installation", "安装便捷性", "展开收纳和固定操作是否方便，不含遮光"),
        ("size_fit", "尺寸覆盖度", "是否能完整覆盖前挡风玻璃"),
        ("storage", "收纳便捷性", "折叠后体积小，收纳是否简便，不含安装"),
        ("stability", "固定稳定性", "使用时是否会移位脱落"),
    ],
    "车载吸尘器": [
        ("suction_power", "吸力强度", "实际吸力大小，细碎垃圾和缝隙吸取效果"),
        ("noise", "噪音", "工作时声响大小"),
        ("battery_life", "续航", "充电后可持续吸尘时间，有线款标注为线长"),
        ("portability", "便携性", "体积和重量，是否方便车内使用"),
        ("cleaning_corners", "死角清洁能力", "座椅缝隙、边角的清洁能力，含附件刷头"),
        ("filter_quality", "过滤效果", "过滤细颗粒能力，是否反尘"),
    ],
}

for sub, delta in AUTOMOTIVE.items():
    write_yaml("automotive", sub, delta)

# ── OFFICE 办公用品 ─────────────────────────────────────────────────────────────
OFFICE = {
    "办公椅": [
        ("lumbar_support", "腰部支撑", "腰托对腰椎的支撑效果，仅限腰部支撑维度"),
        ("ergonomics", "人体工学设计", "整体符合人体工学，含头枕、坐深，不含单独腰托"),
        ("comfort", "长坐舒适度", "久坐2小时以上的舒适感，不含腰托"),
        ("adjustability", "可调节性", "座高/扶手/靠背角度的调节范围和精准度"),
        ("stability", "底座/轮子稳定", "底座承重稳定，滚轮顺滑度，不含组装"),
        ("breathability", "座面透气", "座垫材质是否透气不闷热"),
        ("size_fit", "体型适配", "适合的身高/体重范围"),
    ],
    "显示器支架": [
        ("stability", "稳固不晃动", "调整后是否稳定，重量级显示器是否下沉"),
        ("adjustability", "调节范围", "旋转/俯仰/高度/横竖屏切换调节幅度"),
        ("compatibility", "显示器适配", "VESA孔位支持范围，承重是否足够"),
        ("installation", "安装方式", "夹桌/打孔安装便捷度，不含稳固性"),
        ("cable_management", "走线管理", "机臂是否可内置走线，整洁度"),
    ],
    "桌面收纳": [
        ("capacity", "分区容量", "各格子实际可容纳的物品数量"),
        ("organization", "分区设计", "分区是否合理，取放常用物是否方便"),
        ("stability", "放置稳固", "放桌面是否晃动，不含底部防滑"),
        ("size_fit", "桌面尺寸适配", "整体尺寸是否与桌面空间相符"),
        ("transparency", "可视性", "是否方便快速找到所需物品"),
    ],
    "打印机墨盒": [
        ("print_quality", "打印色彩质量", "打印文字/图片清晰度和色彩还原"),
        ("page_yield", "出墨量/打印页数", "实际打印张数，不含打印质量"),
        ("compatibility", "打印机兼容性", "是否被打印机识别，不报错"),
        ("installation", "安装识别顺畅", "墨盒安装是否顺畅，打印机是否识别"),
        ("color_accuracy", "颜色还原准确", "颜色与屏幕/原件是否接近，不含清晰度"),
    ],
    "鼠标垫": [
        ("surface_texture", "表面手感/滑动", "鼠标在表面滑动的阻力感和顺滑度"),
        ("non_slip", "底部防滑", "鼠标垫是否跑位滑动"),
        ("size_fit", "尺寸大小", "垫子实际大小是否与需求匹配"),
        ("washing_durability", "清洗后耐久", "水洗后是否变形、褪色"),
        ("edge_stitching", "边缘车边质量", "四周包边是否整洁、不起毛边"),
    ],
}

for sub, delta in OFFICE.items():
    write_yaml("office", sub, delta)

print("\n全部完成！")

