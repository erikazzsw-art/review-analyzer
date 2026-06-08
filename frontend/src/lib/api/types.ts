export type WorkspaceRole = "运营" | "产研" | "质检" | "管理者";

export type WorkspaceSummary = {
  role: WorkspaceRole;
  intro: {
    headline: string;
    focus: string;
  };
  metrics: {
    product_count: number;
    risk_product_count: number;
    open_action_count: number;
    open_tracker_count: number;
    recent_upload_count: number;
  };
  today_tasks: Array<{
    category: string;
    title: string;
    description: string;
    cta_label: string;
    page: string;
    session_updates: Record<string, string | number | null>;
  }>;
  risk_products: Array<{
    product_id: string | null;
    product_name: string;
    negative_rate: number;
    top_issue: string;
    pending_review_count: number;
    review_count: number;
    latest_session_label: string;
  }>;
  pending_trackers: Array<{
    title: string;
    product_name: string;
    tag_name: string;
    status: string;
    baseline_pct: number | null;
    current_pct: number | null;
    review_scope: string;
  }>;
  role_action_summary: Array<{
    role: string;
    count: number;
  }>;
  recent_sessions: Array<{
    session_id: number;
    title: string;
    product_id: string;
    workflow_purpose: string;
    created_at: string;
    total_reviews: number;
  }>;
  generated_at: string;
};

export type ProductVariant = {
  id: number | null;
  user_id: number | null;
  product_id: number | null;
  variant_sku: string | null;
  child_asin: string | null;
  color: string | null;
  size: string | null;
  style: string | null;
  material: string | null;
  status: string | null;
  launched_at: string | null;
  created_at: string | null;
};

export type ProductVersion = {
  id: number | null;
  user_id: number | null;
  product_id: number | null;
  variant_id: number | null;
  version_name: string | null;
  version_notes: string | null;
  change_summary: string | null;
  launched_at: string | null;
  is_current: boolean | null;
  created_at: string | null;
};

export type ProductOverview = {
  id: number | null;
  parent_product_id: string;
  name: string | null;
  platform: string | null;
  category: string | null;
  lifecycle_stage: string | null;
  current_version: string;
  core_selling_points: string | null;
  main_competitors: string | null;
  owner_role: string | null;
  production_cycle_days: number | null;
  is_archived_from_sessions: boolean;
  review_count: number;
  positive_rate: number;
  negative_rate: number;
  top_issue: string | null;
  top_highlight: string | null;
  variant_count: number;
  variants: ProductVariant[];
  versions: ProductVersion[];
  session_count: number;
  pending_review_count: number;
  latest_session_label: string | null;
  latest_updated_at: string | null;
};

export type ProductsResponse = {
  items: ProductOverview[];
  total: number;
  generated_at: string;
};

export type AnalysisCommentInput = {
  content: string;
  date: string;
  rating?: number | null;
  reviewer?: string | null;
  source?: string | null;
  raw_data?: Record<string, unknown> | null;
};

export type UploadJob = {
  id: number;
  user_id: number;
  status: "queued" | "processing" | "done" | "failed";
  source_filename: string;
  product_id: string;
  version: string;
  workflow_purpose: string | null;
  product_ref_id: number | null;
  variant_ref_id: number | null;
  total_rows: number;
  processed_rows: number;
  positive_count: number;
  negative_count: number;
  session_id: number | null;
  error_message: string | null;
  payload_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

export type UploadJobResponse = {
  ok: boolean;
  job: UploadJob;
  message: string;
};

export type AnalysisResultModule = {
  summary: string;
  rows: Array<Record<string, unknown>>;
  evidence: string[];
  positive: Array<Record<string, unknown>>;
  negative: Array<Record<string, unknown>>;
};

export type AnalysisSession = {
  id: number;
  user_id: number;
  product_id: string;
  version: string;
  auto_title: string | null;
  custom_title: string | null;
  date_range_start: string | null;
  date_range_end: string | null;
  total_reviews: number;
  positive_count: number;
  negative_count: number;
  category: string | null;
  prompt_version: string | null;
  version_notes: string | null;
  workflow_purpose: string | null;
  product_ref_id: number | null;
  variant_ref_id: number | null;
  created_at: string;
};

export type AnalysisSessionResultsResponse = {
  session: AnalysisSession;
  context: Record<string, unknown>;
  modules: Record<string, AnalysisResultModule>;
  comments: Array<Record<string, unknown>>;
  generated_at: string;
};

export type AnalysisCompareGroup = {
  label: string;
  description: string;
  session_ids: number[];
  product_id: string | null;
  versions: string[];
  product_ref_id: number | null;
  variant_ref_id: number | null;
  review_count: number;
  valid_review_count: number;
  positive_rate: number;
  negative_rate: number;
  avg_rating: number | null;
  top_issue: string;
  top_highlight: string;
  top_issues: Array<Record<string, unknown>>;
  top_highlights: Array<Record<string, unknown>>;
  representative_reviews: Record<string, Array<Record<string, unknown>>>;
};

export type AnalysisCompareResponse = {
  compare_type: string;
  groups: AnalysisCompareGroup[];
  comparison_rows: Array<Record<string, unknown>>;
  issue_differences: Array<Record<string, unknown>>;
  highlight_differences: Array<Record<string, unknown>>;
  risk_groups: AnalysisCompareGroup[];
  opportunity_groups: AnalysisCompareGroup[];
  recommended_actions: string[];
  empty_groups: string[];
  generated_at: string;
};

export type AnalysisHistorySession = {
  id: number;
  product_id: string;
  version: string;
  title: string;
  workflow_purpose: string;
  created_at: string;
  total_reviews: number;
  positive_count: number;
  negative_count: number;
};

export type AnalysisHistoryProduct = {
  product_id: string;
  sessions: AnalysisHistorySession[];
};

export type AnalysisHistoryResponse = {
  items: AnalysisHistoryProduct[];
  total: number;
  selected_session_id: number | null;
  selected_product_id: string | null;
  generated_at: string;
};

export type ComparisonReportCreatePayload = {
  compareType: string;
  sessionIds: number[];
  productId?: string;
  focusFeature?: string;
  title?: string;
};

export type ComparisonReport = {
  id: number;
  user_id: number;
  comparison_type: string;
  title: string | null;
  filters_json: Record<string, unknown> | null;
  result_snapshot: Record<string, unknown> | null;
  summary: string | null;
  recommendations: string | null;
  created_at: string;
};

export type ComparisonReportResponse = {
  report: ComparisonReport;
  dataset: AnalysisCompareResponse;
  ai_summary: {
    headline: string;
    summary: string[];
    recommendations: string[];
    risks: string[];
  } | null;
};

export type QaProduct = {
  id: number | null;
  parent_product_id: string;
  name: string | null;
  review_count: number;
  negative_rate: number;
  latest_session_label: string | null;
};

export type QaCitation = {
  id: number | null;
  product_id: string | null;
  version: string | null;
  session_id: number | null;
  date: string | null;
  rating: number | null;
  content: string | null;
  issue_tag: string | null;
  highlight_tag: string | null;
  sentiment: string | null;
};

export type QaAskResponse = {
  answer: string;
  retrieval_method: string;
  selected_products: QaProduct[];
  citations: QaCitation[];
};

export type QaAskPayload = {
  productIds: string[];
  question: string;
  topK?: number;
};

export type ActionItem = {
  id: number;
  user_id: number;
  product_id: number | null;
  variant_id: number | null;
  session_id: number | null;
  source_product_id: string | null;
  source_version: string | null;
  source_batch_label: string | null;
  title: string;
  tag_name: string | null;
  tag_type: string | null;
  current_pct: number | null;
  owner_role: string | null;
  suggested_action: string | null;
  expected_effect_batch: string | null;
  expected_review_at: string | null;
  status: string;
  created_at: string | null;
  parent_product_id: string | null;
  product_name: string | null;
  variant_sku: string | null;
  child_asin: string | null;
};

export type ActionItemsResponse = {
  items: ActionItem[];
  total: number;
};

export type ActionItemCreatePayload = {
  productId?: number | null;
  variantId?: number | null;
  sessionId?: number | null;
  sourceProductId?: string | null;
  sourceVersion?: string | null;
  sourceBatchLabel?: string | null;
  title: string;
  tagName?: string | null;
  tagType?: string;
  currentPct?: number | null;
  ownerRole?: string | null;
  suggestedAction?: string | null;
  expectedEffectBatch?: string | null;
  expectedReviewAt?: string | null;
  status?: string;
};

export type ActionStatusUpdatePayload = {
  status: string;
};

export type ReviewTracker = {
  id: number;
  user_id: number;
  action_item_id: number | null;
  product_id: number | null;
  variant_id: number | null;
  tracker_title: string;
  tag_name: string | null;
  baseline_pct: number | null;
  improvement_action: string | null;
  effective_batch: string | null;
  review_scope: string | null;
  current_pct: number | null;
  result_status: string;
  conclusion: string | null;
  closed_at: string | null;
  created_at: string | null;
  action_title: string | null;
  source_product_id: string | null;
  source_version: string | null;
  expected_review_at: string | null;
  parent_product_id: string | null;
  product_name: string | null;
  variant_sku: string | null;
  child_asin: string | null;
};

export type ReviewTrackersResponse = {
  items: ReviewTracker[];
  total: number;
};

export type ReviewTrackerCreatePayload = {
  actionItemId?: number | null;
  productId?: number | null;
  variantId?: number | null;
  trackerTitle: string;
  tagName?: string | null;
  baselinePct?: number | null;
  improvementAction?: string | null;
  effectiveBatch?: string | null;
  reviewScope?: string | null;
  currentPct?: number | null;
  resultStatus?: string;
  conclusion?: string | null;
};

export type ReviewTrackerUpdatePayload = {
  reviewScope?: string | null;
  currentPct?: number | null;
  resultStatus: string;
  conclusion?: string | null;
};

export type ReviewTrackerFromActionResponse = {
  tracker: ReviewTracker;
  action: ActionItem;
};

export type PushRuleSettings = {
  issue_pct_enabled: boolean;
  issue_pct_threshold: number;
  neg_rate_enabled: boolean;
  neg_rate_threshold: number;
  neg_rate_compare_enabled: boolean;
  neg_rate_compare_threshold: number;
  neg_rate_compare_window: string;
  neg_rate_compare_version: string;
  issue_compare_enabled: boolean;
  issue_compare_threshold: number;
  issue_compare_window: string;
  issue_compare_version: string;
  highlight_pct_enabled: boolean;
  highlight_pct_threshold: number;
  highlight_compare_enabled: boolean;
  highlight_compare_threshold: number;
  highlight_compare_window: string;
  highlight_compare_version: string;
  auto_push_new_batch: boolean;
};

export type ProductRuleSettings = {
  product_id: string;
  name: string | null;
  issue_pct: number;
  neg_rate: number;
  hl_pct: number;
  enabled: boolean;
  compare_window?: string | null;
  compare_version?: string | null;
};

export type SettingsResponse = {
  webhook_url: string;
  webhook_secret: string;
  webhook_group_name: string;
  api_key: string;
  rules: PushRuleSettings;
  product_rules: ProductRuleSettings[];
  billing: {
    plan?: string;
    configured?: boolean;
    [key: string]: unknown;
  };
  generated_at: string | null;
};

export type SettingsUpdatePayload = {
  webhookUrl: string;
  webhookSecret: string;
  webhookGroupName: string;
  apiKey: string;
  rules: PushRuleSettings;
  productRules: ProductRuleSettings[];
};

export type BillingCheckoutResponse = {
  checkout_html: string;
  configured: boolean;
  plan: string;
};

export type CopywriterPlatformType = {
  id: string;
  name_zh: string;
  name_en: string;
  limit: number;
};

export type CopywriterPlatform = {
  id: string;
  name_zh: string;
  name_en: string;
  icon: string;
  label_zh: string;
  label_en: string;
  sub: string;
  types: CopywriterPlatformType[];
  prohibited: string[];
  guidelines_zh: string;
  guidelines_en: string;
};

export type CopywriterSession = {
  session_id: number;
  product_id: string;
  version: string;
  label: string;
  total_reviews: number;
  positive_count: number;
  negative_count: number;
  created_at: string;
};

export type CopywriterProduct = {
  product_id: string;
  product_name: string | null;
  sessions: CopywriterSession[];
};

export type CopywriterGeneratedItem = {
  type_id: string;
  type_name: string;
  limit: number;
  style: string;
  en: string;
  zh: string;
  char_count: number;
  compliant: boolean;
};

export type CopywriterIdealProfile = {
  features: string[];
  price_range: string;
  logistics: string;
  packaging: string;
  service: string;
  summary: string;
};

export type CopywriterGenerateResponse = {
  platform: CopywriterPlatform;
  selected_sessions: CopywriterSession[];
  review_summary: string;
  generated_items: CopywriterGeneratedItem[];
  ideal_profile: CopywriterIdealProfile | null;
  generated_at: string;
};
