-- 5.9.6-D WP7: Label Registry Audit Events & Proposals
-- Migration: 060_label_registry_audit_and_proposal.sql
-- Status: PENDING ERIKA APPROVAL (high-risk: new tables)
--
-- Decision n: audit events are machine-written, proposals are machine-generated
-- candidates for human review. Neither auto-modifies the registry YAML.
--
-- Attention: Run on dev first, validate, then request Erika approval for prod.

-- ---------------------------------------------------------------------------
-- Table 1: Audit events (machine-written)
-- Records: resolver rejections, shadow diffs, human-flagged mislabels
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS label_registry_audit_events (
    id              BIGSERIAL PRIMARY KEY,
    event_type      TEXT NOT NULL,  -- 'resolver_reject' | 'shadow_diff' | 'human_flag'
    label_key       TEXT NOT NULL,
    sub_category    TEXT NOT NULL DEFAULT '',
    category        TEXT NOT NULL DEFAULT '',
    reject_reason   TEXT,           -- ResolutionRejectReason value for resolver_reject
    existing_display_label TEXT DEFAULT '',
    context         TEXT DEFAULT '', -- free-text note
    source          TEXT DEFAULT 'system', -- 'system' | 'human:<user_id>'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_label
    ON label_registry_audit_events (label_key, event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_created
    ON label_registry_audit_events (created_at DESC);

-- ---------------------------------------------------------------------------
-- Table 2: Registry proposals (machine-generated, human-reviewed)
-- Decision n: 4 closed action types only.
-- proposal_status: 'pending' | 'approved' | 'rejected' | 'applied'
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS label_registry_proposals (
    id                  BIGSERIAL PRIMARY KEY,
    label_key           TEXT NOT NULL,
    action_type         TEXT NOT NULL,
    -- action_type ∈ {scope_adjust, alias_merge, blocked_rule, negative_example}
    -- Per decision n: this is a CLOSED enumeration. Do NOT add a 5th type.

    proposal_data       JSONB NOT NULL DEFAULT '{}',
    -- shape depends on action_type:
    --   scope_adjust:     {scope_policy, aspect_keys, reason}
    --   alias_merge:      {source_keys, target_key, reason}
    --   blocked_rule:     {sub_categories, context_markers, reason}
    --   negative_example: {type, sub_category, review_text, why_not}

    evidence_summary    TEXT DEFAULT '',
    -- human-readable summary of the evidence supporting this proposal

    proposal_status     TEXT NOT NULL DEFAULT 'pending',
    -- 'pending' | 'approved' | 'rejected' | 'applied'

    reviewer_note       TEXT DEFAULT '',
    -- filled by human reviewer on approve/reject

    reviewed_by         TEXT DEFAULT '',
    -- user_id of the reviewer

    reviewed_at         TIMESTAMPTZ,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proposals_label
    ON label_registry_proposals (label_key, action_type);
CREATE INDEX IF NOT EXISTS idx_proposals_status
    ON label_registry_proposals (proposal_status, created_at DESC);
