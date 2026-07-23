-- Step C9.8: Specific Issue two-layer tagging MVP.
-- Aspect remains the stable taxonomy dimension; Specific Issue is the front-stage issue label.

CREATE TABLE IF NOT EXISTS specific_issue_catalog (
    id SERIAL PRIMARY KEY,
    sub_category TEXT NOT NULL,
    aspect_key TEXT NOT NULL,
    canonical_issue_key TEXT NOT NULL,
    specific_issue TEXT NOT NULL,
    display_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    issue_confidence TEXT NOT NULL DEFAULT 'medium',
    issue_ruleset_version TEXT NOT NULL DEFAULT '2026-07-23-mvp1',
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(sub_category, aspect_key, canonical_issue_key)
);

CREATE TABLE IF NOT EXISTS specific_issue_alias_rules (
    id SERIAL PRIMARY KEY,
    sub_category TEXT NOT NULL DEFAULT '*',
    aspect_key TEXT NOT NULL DEFAULT '*',
    rule_type TEXT NOT NULL CHECK (rule_type IN ('exact', 'regex', 'blocklist')),
    pattern TEXT NOT NULL,
    canonical_issue_key TEXT,
    specific_issue TEXT,
    display_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    issue_confidence TEXT NOT NULL DEFAULT 'medium',
    issue_ruleset_version TEXT NOT NULL DEFAULT '2026-07-23-mvp1',
    priority INTEGER NOT NULL DEFAULT 100,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE action_items
    ADD COLUMN IF NOT EXISTS aspect_key TEXT,
    ADD COLUMN IF NOT EXISTS canonical_issue_key TEXT,
    ADD COLUMN IF NOT EXISTS specific_issue TEXT;

ALTER TABLE review_trackers
    ADD COLUMN IF NOT EXISTS aspect_key TEXT,
    ADD COLUMN IF NOT EXISTS canonical_issue_key TEXT,
    ADD COLUMN IF NOT EXISTS specific_issue TEXT;

CREATE INDEX IF NOT EXISTS idx_specific_issue_catalog_identity
    ON specific_issue_catalog(sub_category, aspect_key, canonical_issue_key);

CREATE INDEX IF NOT EXISTS idx_specific_issue_alias_rules_lookup
    ON specific_issue_alias_rules(sub_category, aspect_key, rule_type, enabled, priority);

CREATE INDEX IF NOT EXISTS idx_action_items_specific_issue
    ON action_items(user_id, aspect_key, canonical_issue_key)
    WHERE removed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_review_trackers_specific_issue
    ON review_trackers(user_id, aspect_key, canonical_issue_key);
