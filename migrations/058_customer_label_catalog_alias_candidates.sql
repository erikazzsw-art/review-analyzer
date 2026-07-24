-- Step C9.8 Phase 2: unified Customer Issue / Customer Label data layer.
-- This migration adds the canonical catalog, alias rules, and candidate pool used
-- by both issue and highlight labels. It intentionally does not create
-- occurrence-level storage; that belongs to a later phase.

CREATE TABLE IF NOT EXISTS customer_label_catalog (
    id BIGSERIAL PRIMARY KEY,
    label_type TEXT NOT NULL CHECK (label_type IN ('issue', 'highlight')),
    canonical_label_key TEXT NOT NULL,
    display_en TEXT NOT NULL,
    display_zh TEXT NOT NULL DEFAULT '',
    primary_aspect_key TEXT NOT NULL DEFAULT '',
    aspect_keys TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
    scope_level TEXT NOT NULL DEFAULT 'global'
        CHECK (scope_level IN ('global', 'category', 'sub_category')),
    category_key TEXT NOT NULL DEFAULT '*',
    sub_category_key TEXT NOT NULL DEFAULT '*',
    display_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'disabled', 'deprecated', 'merged')),
    source TEXT NOT NULL DEFAULT 'system'
        CHECK (source IN ('system', 'human', 'legacy_import')),
    ruleset_version TEXT NOT NULL DEFAULT '2026-07-24-customer-label-catalog-v1',
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(label_type, canonical_label_key, scope_level, category_key, sub_category_key)
);

CREATE TABLE IF NOT EXISTS customer_label_alias_rules (
    id BIGSERIAL PRIMARY KEY,
    label_type TEXT NOT NULL CHECK (label_type IN ('issue', 'highlight')),
    scope_level TEXT NOT NULL DEFAULT 'global'
        CHECK (scope_level IN ('global', 'category', 'sub_category')),
    category_key TEXT NOT NULL DEFAULT '*',
    sub_category_key TEXT NOT NULL DEFAULT '*',
    aspect_key TEXT NOT NULL DEFAULT '*',
    rule_type TEXT NOT NULL CHECK (rule_type IN ('exact', 'contains', 'regex', 'blocklist')),
    pattern TEXT NOT NULL,
    normalized_pattern TEXT NOT NULL DEFAULT '',
    canonical_label_key TEXT,
    display_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    confidence TEXT NOT NULL DEFAULT 'medium'
        CHECK (confidence IN ('high', 'medium', 'low')),
    priority INTEGER NOT NULL DEFAULT 100,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source TEXT NOT NULL DEFAULT 'system'
        CHECK (source IN ('system', 'human', 'legacy_import')),
    ruleset_version TEXT NOT NULL DEFAULT '2026-07-24-customer-label-catalog-v1',
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customer_label_candidates (
    id BIGSERIAL PRIMARY KEY,
    label_type TEXT NOT NULL CHECK (label_type IN ('issue', 'highlight')),
    raw_label TEXT NOT NULL,
    normalized_raw_label TEXT NOT NULL,
    category_key TEXT NOT NULL DEFAULT '*',
    sub_category_key TEXT NOT NULL DEFAULT '*',
    aspect_key TEXT NOT NULL DEFAULT '',
    suggested_canonical_label_key TEXT,
    suggested_display_en TEXT,
    suggested_display_zh TEXT,
    occurrence_count INTEGER NOT NULL DEFAULT 0,
    review_count INTEGER NOT NULL DEFAULT 0,
    sample_evidence_spans JSONB NOT NULL DEFAULT '[]'::JSONB,
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'needs_review', 'approved', 'merged', 'rejected', 'ignored')),
    source TEXT NOT NULL DEFAULT 'system'
        CHECK (source IN ('system', 'human', 'legacy_import')),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    note TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(label_type, normalized_raw_label, category_key, sub_category_key, aspect_key)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_customer_label_alias_rules_identity
    ON customer_label_alias_rules (
        label_type,
        scope_level,
        category_key,
        sub_category_key,
        aspect_key,
        rule_type,
        normalized_pattern,
        COALESCE(canonical_label_key, '')
    );

CREATE INDEX IF NOT EXISTS idx_customer_label_catalog_lookup
    ON customer_label_catalog (
        label_type,
        canonical_label_key,
        scope_level,
        category_key,
        sub_category_key,
        status
    );

CREATE INDEX IF NOT EXISTS idx_customer_label_catalog_aspects
    ON customer_label_catalog USING GIN (aspect_keys);

CREATE INDEX IF NOT EXISTS idx_customer_label_alias_rules_lookup
    ON customer_label_alias_rules (
        label_type,
        scope_level,
        category_key,
        sub_category_key,
        aspect_key,
        enabled,
        priority
    );

CREATE INDEX IF NOT EXISTS idx_customer_label_candidates_status
    ON customer_label_candidates(label_type, status, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_customer_label_candidates_scope
    ON customer_label_candidates(label_type, category_key, sub_category_key, aspect_key);

WITH seed(label_type, canonical_label_key, display_en, display_zh, primary_aspect_key, scope_level) AS (
    VALUES
        ('issue', 'arrived_damaged', 'Arrived Damaged', '到货破损', 'shipping_damage', 'global'),
        ('issue', 'battery_dies_quickly', 'Battery Dies Quickly', '电池耗电快', 'battery_life', 'global'),
        ('issue', 'breaks_easily', 'Breaks Easily', '容易损坏', 'durability', 'global'),
        ('issue', 'charging_fails', 'Charging Fails', '充电不稳定', 'charging', 'global'),
        ('issue', 'curl_does_not_hold', 'Curl Does Not Hold', '卷翘保持差', 'curl_hold', 'global'),
        ('issue', 'falls_apart', 'Falls Apart', '容易散架', 'durability', 'global'),
        ('issue', 'feels_thin_and_flimsy', 'Feels Thin and Flimsy', '材质偏薄不结实', 'material', 'global'),
        ('issue', 'hard_to_assemble', 'Hard To Assemble', '组装困难', 'assembly', 'global'),
        ('issue', 'instructions_unclear', 'Instructions Unclear', '说明不清楚', 'instructions', 'global'),
        ('issue', 'irritates_eyes', 'Irritates Eyes', '刺激眼睛', 'eye_sensitivity', 'global'),
        ('issue', 'makes_squeaking_noise', 'Makes Squeaking Noise', '有异响', 'noise', 'global'),
        ('issue', 'mascara_clumps', 'Mascara Clumps', '睫毛膏容易结块', 'clumping', 'global'),
        ('issue', 'mascara_flakes', 'Mascara Flakes', '睫毛膏容易掉渣', 'flaking', 'global'),
        ('issue', 'missing_parts', 'Missing Parts', '缺少配件', 'missing_parts', 'global'),
        ('issue', 'missing_wader_hanger', 'Missing Wader Hanger', '缺少涉水裤挂架', 'accessory_storage', 'global'),
        ('issue', 'not_breathable', 'Not Breathable', '不够透气', 'breathability', 'global'),
        ('issue', 'not_enough_length', 'Not Enough Length', '纤长效果不足', 'lengthening_effect', 'global'),
        ('issue', 'not_enough_volume', 'Not Enough Volume', '浓密效果不足', 'volumizing_effect', 'global'),
        ('issue', 'not_worth_the_price', 'Not Worth the Price', '不值这个价格', 'value_for_money', 'global'),
        ('issue', 'pocket_not_waterproof', 'Pocket Not Waterproof', '口袋不防水', 'accessory_storage', 'global'),
        ('issue', 'pocket_too_small', 'Pocket Too Small', '口袋太小', 'accessory_storage', 'global'),
        ('issue', 'poor_customer_service', 'Poor Customer Service', '客服体验差', 'customer_service', 'global'),
        ('issue', 'runs_too_large', 'Runs Too Large', '尺码偏大', 'size_fit', 'global'),
        ('issue', 'runs_too_small', 'Runs Too Small', '尺码偏小', 'size_fit', 'global'),
        ('issue', 'smudges_easily', 'Smudges Easily', '容易晕染', 'smudge_resistance', 'global'),
        ('issue', 'strong_chemical_smell', 'Strong Chemical Smell', '化学气味重', 'smell', 'global'),
        ('issue', 'uncomfortable_fit', 'Uncomfortable Fit', '穿着不舒服', 'comfort', 'global'),
        ('issue', 'water_leaks_through', 'Water Leaks Through', '容易进水', 'waterproof', 'global'),
        ('issue', 'zipper_fails', 'Zipper Fails', '拉链容易故障', 'zipper_quality', 'global'),
        ('highlight', 'adds_noticeable_length', 'Adds Noticeable Length', '纤长效果明显', 'lengthening_effect', 'global'),
        ('highlight', 'adds_visible_volume', 'Adds Visible Volume', '浓密效果明显', 'volumizing_effect', 'global'),
        ('highlight', 'arrives_on_time_and_intact', 'Arrives On Time and Intact', '到货及时完好', 'shipping_damage', 'global'),
        ('highlight', 'breathes_well', 'Breathes Well', '透气性好', 'breathability', 'global'),
        ('highlight', 'charges_reliably', 'Charges Reliably', '充电稳定', 'charging', 'global'),
        ('highlight', 'comfortable_to_wear', 'Comfortable To Wear', '穿着舒适', 'comfort', 'global'),
        ('highlight', 'does_not_smudge', 'Does Not Smudge', '不易晕染', 'smudge_resistance', 'global'),
        ('highlight', 'easy_to_use', 'Easy To Use', '使用方便', 'ease_of_use', 'global'),
        ('highlight', 'feels_well_made', 'Feels Well Made', '做工扎实', 'build_quality', 'global'),
        ('highlight', 'fits_as_expected', 'Fits as Expected', '尺码合适', 'size_fit', 'global'),
        ('highlight', 'good_traction', 'Good Traction', '抓地稳', 'grip', 'global'),
        ('highlight', 'good_value_for_the_price', 'Good Value for the Price', '性价比高', 'value_for_money', 'global'),
        ('highlight', 'holds_curl_well', 'Holds Curl Well', '卷翘保持好', 'curl_hold', 'global'),
        ('highlight', 'holds_up_well', 'Holds Up Well', '耐用可靠', 'durability', 'global'),
        ('highlight', 'keeps_water_out', 'Keeps Water Out', '防水可靠', 'waterproof', 'global'),
        ('highlight', 'long_battery_life', 'Long Battery Life', '续航时间长', 'battery_life', 'global'),
        ('highlight', 'looks_good', 'Looks Good', '外观好看', 'aesthetics', 'global'),
        ('highlight', 'no_strong_odor', 'No Strong Odor', '没有明显异味', 'smell', 'global'),
        ('highlight', 'separates_without_clumps', 'Separates Without Clumps', '不易结块根根分明', 'clumping', 'global'),
        ('highlight', 'useful_storage_space', 'Useful Storage Space', '收纳空间实用', 'accessory_storage', 'global')
)
INSERT INTO customer_label_catalog (
    label_type,
    canonical_label_key,
    display_en,
    display_zh,
    primary_aspect_key,
    aspect_keys,
    scope_level,
    category_key,
    sub_category_key,
    source
)
SELECT
    label_type,
    canonical_label_key,
    display_en,
    display_zh,
    primary_aspect_key,
    ARRAY[primary_aspect_key]::TEXT[],
    scope_level,
    '*',
    '*',
    'system'
FROM seed
ON CONFLICT (label_type, canonical_label_key, scope_level, category_key, sub_category_key)
DO UPDATE SET
    display_en = EXCLUDED.display_en,
    display_zh = EXCLUDED.display_zh,
    primary_aspect_key = EXCLUDED.primary_aspect_key,
    aspect_keys = EXCLUDED.aspect_keys,
    display_allowed = TRUE,
    status = 'active',
    updated_at = NOW();

WITH broad(label_type, pattern, normalized_pattern) AS (
    VALUES
        ('issue', 'Accessories & Storage', 'accessories and storage'),
        ('issue', 'Accessory Storage', 'accessory storage'),
        ('issue', 'Aesthetics', 'aesthetics'),
        ('issue', 'Assembly', 'assembly'),
        ('issue', 'Build Quality', 'build quality'),
        ('issue', 'Capacity', 'capacity'),
        ('issue', 'Comfort', 'comfort'),
        ('issue', 'Durability', 'durability'),
        ('issue', 'Ease of Use', 'ease of use'),
        ('issue', 'Material', 'material'),
        ('issue', 'Materials', 'materials'),
        ('issue', 'Other', 'other'),
        ('issue', 'Packaging', 'packaging'),
        ('issue', 'Product Quality', 'product quality'),
        ('issue', 'Quality', 'quality'),
        ('issue', 'Waterproof', 'waterproof'),
        ('issue', 'Waterproof Performance', 'waterproof performance'),
        ('issue', 'Waterproofing', 'waterproofing'),
        ('highlight', 'Accessories & Storage', 'accessories and storage'),
        ('highlight', 'Accessory Storage', 'accessory storage'),
        ('highlight', 'Aesthetics', 'aesthetics'),
        ('highlight', 'Build Quality', 'build quality'),
        ('highlight', 'Comfort', 'comfort'),
        ('highlight', 'Durability', 'durability'),
        ('highlight', 'Ease of Use', 'ease of use'),
        ('highlight', 'Material', 'material'),
        ('highlight', 'Materials', 'materials'),
        ('highlight', 'Other', 'other'),
        ('highlight', 'Packaging', 'packaging'),
        ('highlight', 'Product Quality', 'product quality'),
        ('highlight', 'Quality', 'quality'),
        ('highlight', 'Waterproof', 'waterproof'),
        ('highlight', 'Waterproof Performance', 'waterproof performance'),
        ('highlight', 'Waterproofing', 'waterproofing')
)
INSERT INTO customer_label_alias_rules (
    label_type,
    rule_type,
    pattern,
    normalized_pattern,
    canonical_label_key,
    display_allowed,
    confidence,
    priority,
    source
)
SELECT
    label_type,
    'blocklist',
    pattern,
    normalized_pattern,
    NULL,
    FALSE,
    'high',
    10,
    'system'
FROM broad
ON CONFLICT DO NOTHING;

WITH alias(label_type, aspect_key, rule_type, pattern, normalized_pattern, canonical_label_key, priority) AS (
    VALUES
        ('issue', 'accessory_storage', 'exact', 'pocket gets wet', 'pocket gets wet', 'pocket_not_waterproof', 20),
        ('issue', 'accessory_storage', 'exact', 'outer pocket not waterproof', 'outer pocket not waterproof', 'pocket_not_waterproof', 20),
        ('issue', 'accessory_storage', 'exact', 'pocket too small', 'pocket too small', 'pocket_too_small', 20),
        ('issue', 'accessory_storage', 'exact', 'missing hanger', 'missing hanger', 'missing_wader_hanger', 20),
        ('issue', 'accessory_storage', 'exact', 'hanger missing', 'hanger missing', 'missing_wader_hanger', 20),
        ('issue', 'waterproof', 'exact', 'leaks water', 'leaks water', 'water_leaks_through', 20),
        ('issue', 'waterproof', 'exact', 'water gets in', 'water gets in', 'water_leaks_through', 20),
        ('highlight', 'waterproof', 'exact', 'kept dry', 'kept dry', 'keeps_water_out', 20),
        ('highlight', 'waterproof', 'exact', 'kept me dry', 'kept me dry', 'keeps_water_out', 20),
        ('highlight', 'waterproof', 'exact', 'no leaks', 'no leaks', 'keeps_water_out', 20),
        ('highlight', 'comfort', 'exact', 'comfortable', 'comfortable', 'comfortable_to_wear', 20),
        ('highlight', 'value_for_money', 'exact', 'good value', 'good value', 'good_value_for_the_price', 20),
        ('highlight', 'build_quality', 'exact', 'well made', 'well made', 'feels_well_made', 20)
)
INSERT INTO customer_label_alias_rules (
    label_type,
    aspect_key,
    rule_type,
    pattern,
    normalized_pattern,
    canonical_label_key,
    confidence,
    priority,
    source
)
SELECT
    label_type,
    aspect_key,
    rule_type,
    pattern,
    normalized_pattern,
    canonical_label_key,
    'high',
    priority,
    'system'
FROM alias
ON CONFLICT DO NOTHING;

INSERT INTO customer_label_catalog (
    label_type,
    canonical_label_key,
    display_en,
    display_zh,
    primary_aspect_key,
    aspect_keys,
    scope_level,
    category_key,
    sub_category_key,
    display_allowed,
    status,
    source,
    ruleset_version,
    metadata
)
SELECT
    'issue',
    canonical_issue_key,
    specific_issue,
    '',
    aspect_key,
    ARRAY[aspect_key]::TEXT[],
    CASE WHEN sub_category = '*' THEN 'global' ELSE 'sub_category' END,
    '*',
    COALESCE(NULLIF(sub_category, ''), '*'),
    display_allowed,
    CASE WHEN display_allowed THEN 'active' ELSE 'disabled' END,
    'legacy_import',
    issue_ruleset_version,
    jsonb_build_object('legacy_table', 'specific_issue_catalog', 'legacy_id', id, 'note', note)
FROM specific_issue_catalog
ON CONFLICT (label_type, canonical_label_key, scope_level, category_key, sub_category_key)
DO UPDATE SET
    display_en = EXCLUDED.display_en,
    primary_aspect_key = EXCLUDED.primary_aspect_key,
    aspect_keys = EXCLUDED.aspect_keys,
    display_allowed = EXCLUDED.display_allowed,
    status = EXCLUDED.status,
    metadata = customer_label_catalog.metadata || EXCLUDED.metadata,
    updated_at = NOW();

INSERT INTO customer_label_alias_rules (
    label_type,
    scope_level,
    category_key,
    sub_category_key,
    aspect_key,
    rule_type,
    pattern,
    normalized_pattern,
    canonical_label_key,
    display_allowed,
    confidence,
    priority,
    enabled,
    source,
    ruleset_version,
    metadata
)
SELECT
    'issue',
    CASE WHEN sub_category = '*' THEN 'global' ELSE 'sub_category' END,
    '*',
    COALESCE(NULLIF(sub_category, ''), '*'),
    COALESCE(NULLIF(aspect_key, ''), '*'),
    rule_type,
    pattern,
    regexp_replace(lower(replace(pattern, '&', ' and ')), '[^a-z0-9]+', ' ', 'g'),
    canonical_issue_key,
    display_allowed,
    issue_confidence,
    priority,
    enabled,
    'legacy_import',
    issue_ruleset_version,
    jsonb_build_object('legacy_table', 'specific_issue_alias_rules', 'legacy_id', id, 'note', note)
FROM specific_issue_alias_rules
ON CONFLICT DO NOTHING;
