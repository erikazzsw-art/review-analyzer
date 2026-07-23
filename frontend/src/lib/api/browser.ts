import type {
  ActionItem,
  ActionItemCreatePayload,
  ActionProductGroup,
  ActionItemsResponse,
  ActionStatusUpdatePayload,
  AnalysisCommentInput,
  AnalysisCompareResponse,
  AnalysisHistoryResponse,
  AnalysisSessionResultsResponse,
  AsinFetchResponse,
  AsinWatchlistCreatePayload,
  AsinWatchlistItem,
  AsinWatchlistResponse,
  AsinWatchlistUpdatePayload,
  BillingCheckoutResponse,
  CompareDatasetRequest,
  CompareExportRequest,
  CompareHistoryResponse,
  CompareLatestResponse,
  CopywriterGenerateResponse,
  CopywriterPlatform,
  CopywriterProductVersionsResponse,
  CopywriterStyle,
  FeedbackCreatePayload,
  FeedbackResponse,
  ProductSearchResponse,
  QaAskPayload,
  QaAskResponse,
  QaConversation,
  QaMessage,
  QaProduct,
  ComparisonReportCreatePayload,
  ComparisonReportResponse,
  ReviewTrackerCreatePayload,
  ReviewTrackerFromActionResponse,
  ReviewTrackerUpdatePayload,
  ReviewTrackersResponse,
  SettingsResponse,
  SettingsUpdatePayload,
  SmartPushSettingsResponse,
  SubCategoryProbeResponse,
  TaxonomyCategoriesResponse,
  UploadJobResponse,
} from "@/lib/api/types";

const DEFAULT_API_BASE_URL = "/api";

function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    return DEFAULT_API_BASE_URL;
  }
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
    process.env.API_BASE_URL?.trim() ||
    DEFAULT_API_BASE_URL
  );
}

type ApiError = {
  status: number;
  message: string;
};

export type DuplicateBatchError = {
  status: 409;
  message: string;
  existingSessionId: number;
  existingTitle: string;
  existingCreatedAt: string;
  totalReviews: number;
};

export function describeRequestError(err: unknown, target: string): string {
  if (err instanceof Error) {
    return `${err.name}: ${err.message} (${target})`;
  }
  return `Request failed (${target})`;
}

async function parseError(response: Response): Promise<ApiError> {
  let message = `Request failed with status ${response.status}.`;
  const fallback = response.clone();
  try {
    const payload = (await response.json()) as { detail?: string };
    if (payload.detail) {
      message = payload.detail;
    }
  } catch {
    try {
      const text = (await fallback.text()).replace(/\s+/g, " ").trim();
      if (text) {
        message = `${message} ${text.slice(0, 160)}`;
      }
    } catch {}
  }
  return { status: response.status, message };
}

async function parseJsonBody<T>(response: Response): Promise<T> {
  const fallback = response.clone();
  try {
    return (await response.json()) as T;
  } catch {
    let preview = "";
    try {
      preview = (await fallback.text()).replace(/\s+/g, " ").trim().slice(0, 160);
    } catch {}
    const contentType = response.headers.get("content-type") || "unknown content-type";
    throw {
      status: response.status,
      message: `Expected JSON from ${response.url || "API response"}, received ${contentType}${preview ? `: ${preview}` : ""}`,
    } satisfies ApiError;
  }
}

export async function submitUploadJob(params: {
  sourceFile: File;
  productId: string;
  version: string;
  workflowPurpose: string;
  productName: string;
  platform: string;
  category: string;
  dateStart: string;
  dateEnd: string;
  versionNotes: string;
  representativeAsin?: string | null;
  productRefId?: number | null;
  variantRefId?: number | null;
}): Promise<UploadJobResponse> {
  const formData = new FormData();
  formData.append("source_file", params.sourceFile);
  formData.append("product_id", params.productId);
  formData.append("version", params.version);
  formData.append("workflow_purpose", params.workflowPurpose);
  formData.append("product_name", params.productName);
  formData.append("platform", params.platform);
  formData.append("category", params.category);
  formData.append("date_start", params.dateStart);
  formData.append("date_end", params.dateEnd);
  formData.append("version_notes", params.versionNotes);
  if (params.representativeAsin?.trim()) {
    formData.append("representative_asin", params.representativeAsin.trim());
  }
  if (params.productRefId !== undefined && params.productRefId !== null) {
    formData.append("product_ref_id", String(params.productRefId));
  }
  if (params.variantRefId !== undefined && params.variantRefId !== null) {
    formData.append("variant_ref_id", String(params.variantRefId));
  }

  const response = await fetch(`${getApiBaseUrl()}/uploads`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });

  if (response.status === 409) {
    const payload = await response.json();
    const err: DuplicateBatchError = {
      status: 409,
      message: payload.detail || "duplicate_batch",
      existingSessionId: payload.existing_session_id,
      existingTitle: payload.existing_title || "",
      existingCreatedAt: payload.existing_created_at || "",
      totalReviews: payload.total_reviews || 0,
    };
    throw err;
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as UploadJobResponse;
}

export async function fetchUploadJob(jobId: number): Promise<UploadJobResponse> {
  const response = await fetch(`${getApiBaseUrl()}/analysis/jobs/${jobId}`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as UploadJobResponse;
}

export async function fetchByAsin(params: {
  asin: string;
  platform?: "amazon" | "aliexpress" | "shopee" | "ebay" | "walmart";
  marketplace: string;
  productName?: string;
  maxPages?: number;
  fetchAllVariants?: boolean;
}): Promise<AsinFetchResponse> {
  const response = await fetch(`${getApiBaseUrl()}/reviews/fetch-by-asin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      asin: params.asin,
      platform: params.platform || "amazon",
      marketplace: params.marketplace,
      product_name: params.productName || undefined,
      max_pages: params.maxPages || 5,
      fetch_all_variants: params.fetchAllVariants || false,
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as AsinFetchResponse;
}

export async function fetchAnalysisSessionResults(
  sessionId: number,
): Promise<AnalysisSessionResultsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/analysis/sessions/${sessionId}/results`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as AnalysisSessionResultsResponse;
}

export async function fetchAnalysisCompare(params?: {
  compareType?: string;
  sessionIds?: number[];
  productId?: string;
}): Promise<AnalysisCompareResponse> {
  const search = new URLSearchParams();
  if (params?.compareType) {
    search.set("compare_type", params.compareType);
  }
  if (params?.productId) {
    search.set("product_id", params.productId);
  }
  (params?.sessionIds || []).forEach((sessionId) => {
    search.append("session_ids", String(sessionId));
  });

  const query = search.toString();
  const response = await fetch(`${getApiBaseUrl()}/analysis/compare${query ? `?${query}` : ""}`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return parseJsonBody<AnalysisCompareResponse>(response);
}

export async function fetchAnalysisHistory(productId?: string): Promise<AnalysisHistoryResponse> {
  const search = new URLSearchParams();
  if (productId) {
    search.set("product_id", productId);
  }
  const query = search.toString();
  const response = await fetch(`${getApiBaseUrl()}/analysis/history${query ? `?${query}` : ""}`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as AnalysisHistoryResponse;
}

export async function searchProducts(q: string, limit = 20): Promise<ProductSearchResponse> {
  const search = new URLSearchParams({ q, limit: String(limit) });
  const response = await fetch(`${getApiBaseUrl()}/products/search?${search.toString()}`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as ProductSearchResponse;
}

export async function submitComparisonReport(
  params: ComparisonReportCreatePayload,
): Promise<ComparisonReportResponse> {
  const response = await fetch(`${getApiBaseUrl()}/compare/reports`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      compare_type: params.compareType,
      session_ids: params.sessionIds,
      product_id: params.productId ?? null,
      focus_feature: params.focusFeature ?? null,
      title: params.title ?? null,
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ComparisonReportResponse;
}

function serializeCompareGroups(request: CompareDatasetRequest | CompareExportRequest) {
  return {
    compare_type: request.compareType,
    groups: request.groups.map((group) => ({
      product_id: group.productId,
      versions: group.versions ?? [],
      date_start: group.dateStart ?? null,
      date_end: group.dateEnd ?? null,
      label: group.label ?? null,
      description: group.description ?? null,
    })),
  };
}

export async function fetchCompareDataset(
  request: CompareDatasetRequest,
): Promise<AnalysisCompareResponse> {
  const response = await fetch(`${getApiBaseUrl()}/compare/dataset`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(serializeCompareGroups(request)),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return parseJsonBody<AnalysisCompareResponse>(response);
}

export async function downloadCompareExport(request: CompareExportRequest): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/compare/export`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...serializeCompareGroups(request),
      include_ai_summary: request.includeAiSummary ?? false,
      focus_feature: request.focusFeature ?? null,
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match ? match[1] : `compare-${new Date().toISOString().slice(0, 10)}.xlsx`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  recordDownload(filename, "对比分析");
}

export async function fetchCompareHistory(
  q?: string,
  limit = 20,
  offset = 0,
): Promise<CompareHistoryResponse> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  const response = await fetch(`${getApiBaseUrl()}/compare/history?${params.toString()}`, {
    method: "GET",
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return parseJsonBody<CompareHistoryResponse>(response);
}

export async function fetchCompareHistoryEntry(
  fingerprint: string,
): Promise<CompareLatestResponse> {
  const response = await fetch(`${getApiBaseUrl()}/compare/history/${fingerprint}`, {
    method: "GET",
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return parseJsonBody<CompareLatestResponse>(response);
}

export async function deleteCompareHistory(fingerprint: string): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/compare/history/${fingerprint}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
}

export async function fetchQaProducts(): Promise<QaProduct[]> {
  const response = await fetch(`${getApiBaseUrl()}/qa/products`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as QaProduct[];
}

export async function askReviews(
  payload: QaAskPayload,
): Promise<QaAskResponse> {
  const response = await fetch(`${getApiBaseUrl()}/qa/ask`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      product_ids: payload.productIds,
      question: payload.question,
      top_k: payload.topK ?? 5,
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as QaAskResponse;
}

export async function createQaConversation(productIds: string[]): Promise<QaConversation> {
  const response = await fetch(`${getApiBaseUrl()}/qa/conversations`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_ids: productIds }),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as QaConversation;
}

export async function sendQaMessage(
  conversationId: number,
  question: string,
  topK: number = 5,
): Promise<QaMessage> {
  const response = await fetch(`${getApiBaseUrl()}/qa/conversations/${conversationId}/messages`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as QaMessage;
}

export async function fetchQaConversationMessages(conversationId: number): Promise<QaMessage[]> {
  const response = await fetch(`${getApiBaseUrl()}/qa/conversations/${conversationId}/messages`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as QaMessage[];
}

export async function fetchActionItems(): Promise<ActionItemsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/actions`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ActionItemsResponse;
}

export async function createActionItem(
  payload: ActionItemCreatePayload,
): Promise<Record<string, unknown>> {
  const response = await fetch(`${getApiBaseUrl()}/actions`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      product_id: payload.productId ?? null,
      variant_id: payload.variantId ?? null,
      session_id: payload.sessionId ?? null,
      source_product_id: payload.sourceProductId ?? null,
      source_version: payload.sourceVersion ?? null,
      source_batch_label: payload.sourceBatchLabel ?? null,
      title: payload.title,
      tag_name: payload.tagName ?? null,
      tag_type: payload.tagType ?? "issue",
      aspect_key: payload.aspectKey ?? null,
      canonical_issue_key: payload.canonicalIssueKey ?? null,
      specific_issue: payload.specificIssue ?? payload.tagName ?? null,
      current_pct: payload.currentPct ?? null,
      owner_role: payload.responsibleDepartment ?? payload.ownerRole ?? null,
      suggested_action: payload.suggestedAction ?? null,
      ai_suggestions: payload.aiSuggestions ?? [],
      expected_effect_batch: payload.expectedEffectBatch ?? null,
      expected_review_at: payload.expectedReviewAt ?? null,
      status: payload.status ?? "in_progress",
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as Record<string, unknown>;
}

export async function updateActionStatus(
  actionId: number,
  status: string,
): Promise<ActionItem> {
  const response = await fetch(`${getApiBaseUrl()}/actions/${actionId}/status`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status } satisfies ActionStatusUpdatePayload),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ActionItem;
}

export async function updateActionSuggestions(
  actionId: number,
  suggestions: string[],
): Promise<ActionItem> {
  const response = await fetch(`${getApiBaseUrl()}/actions/${actionId}/suggestions`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ suggestions }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ActionItem;
}

export async function deleteActionItem(actionId: number): Promise<{ removed: boolean }> {
  const response = await fetch(`${getApiBaseUrl()}/actions/${actionId}`, {
    method: "DELETE",
    credentials: "include",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as { removed: boolean };
}

export async function updateActionProductGroupNote(
  productGroupKey: string,
  note: string | null,
): Promise<ActionProductGroup> {
  const response = await fetch(`${getApiBaseUrl()}/actions/product-groups/note`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ product_group_key: productGroupKey, note }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ActionProductGroup;
}

export async function reorderActionProductGroups(productGroupKeys: string[]): Promise<{ updated: number }> {
  const response = await fetch(`${getApiBaseUrl()}/actions/product-groups/reorder`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ product_group_keys: productGroupKeys }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as { updated: number };
}

export async function removeActionProductGroup(productGroupKey: string): Promise<{ removed: number }> {
  const response = await fetch(`${getApiBaseUrl()}/actions/product-groups/remove`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ product_group_key: productGroupKey }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as { removed: number };
}

export async function reorderActionItems(
  productGroupKey: string,
  actionIds: number[],
): Promise<{ updated: number }> {
  const response = await fetch(`${getApiBaseUrl()}/actions/reorder`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ product_group_key: productGroupKey, action_ids: actionIds }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as { updated: number };
}

export async function getActionTracker(actionId: number): Promise<Record<string, unknown> | null> {
  const response = await fetch(`${getApiBaseUrl()}/actions/${actionId}/tracker`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as Record<string, unknown>;
}

export async function createTrackerFromAction(
  actionId: number,
  payload: ReviewTrackerCreatePayload,
): Promise<ReviewTrackerFromActionResponse> {
  const response = await fetch(`${getApiBaseUrl()}/actions/${actionId}/tracker`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      action_item_id: payload.actionItemId ?? null,
      product_id: payload.productId ?? null,
      variant_id: payload.variantId ?? null,
      tracker_title: payload.trackerTitle,
      tag_name: payload.tagName ?? null,
      aspect_key: payload.aspectKey ?? null,
      canonical_issue_key: payload.canonicalIssueKey ?? null,
      specific_issue: payload.specificIssue ?? payload.tagName ?? null,
      baseline_pct: payload.baselinePct ?? null,
      improvement_action: payload.improvementAction ?? null,
      effective_batch: payload.effectiveBatch ?? null,
      review_scope: payload.reviewScope ?? null,
      current_pct: payload.currentPct ?? null,
      result_status: payload.resultStatus ?? "pending",
      conclusion: payload.conclusion ?? null,
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ReviewTrackerFromActionResponse;
}

export async function fetchReviewTrackers(status?: string): Promise<ReviewTrackersResponse> {
  const search = new URLSearchParams();
  if (status) {
    search.set("tracker_status", status);
  }
  const query = search.toString();
  const response = await fetch(`${getApiBaseUrl()}/actions/trackers${query ? `?${query}` : ""}`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ReviewTrackersResponse;
}

export async function updateReviewTracker(
  trackerId: number,
  payload: ReviewTrackerUpdatePayload,
): Promise<Record<string, unknown>> {
  const response = await fetch(`${getApiBaseUrl()}/actions/trackers/${trackerId}`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      review_scope: payload.reviewScope ?? null,
      current_pct: payload.currentPct ?? null,
      result_status: payload.resultStatus,
      conclusion: payload.conclusion ?? null,
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as Record<string, unknown>;
}

export function normalizeCommentInput(
  input: AnalysisCommentInput,
): AnalysisCommentInput {
  return {
    content: input.content.trim(),
    date: input.date.trim(),
    rating: input.rating ?? null,
    reviewer: input.reviewer?.trim() || null,
    source: input.source?.trim() || null,
    raw_data: input.raw_data ?? null,
  };
}

export async function fetchSettings(): Promise<SettingsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/settings`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as SettingsResponse;
}

export async function saveSettings(payload: SettingsUpdatePayload): Promise<SettingsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/settings`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      webhook_platform: payload.webhookPlatform,
      webhook_url: payload.webhookUrl,
      webhook_secret: payload.webhookSecret,
      webhook_group_name: payload.webhookGroupName,
      api_key: payload.apiKey,
      rules: payload.rules,
      product_rules: payload.productRules,
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as SettingsResponse;
}

export async function testWebhook(payload: {
  webhookPlatform: "feishu" | "dingtalk" | "wechat";
  webhookUrl: string;
  webhookSecret: string;
}): Promise<Record<string, unknown>> {
  const response = await fetch(`${getApiBaseUrl()}/settings/test-webhook`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      webhook_platform: payload.webhookPlatform,
      webhook_url: payload.webhookUrl,
      webhook_secret: payload.webhookSecret,
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as Record<string, unknown>;
}

export async function fetchCopywriterPlatforms(): Promise<CopywriterPlatform[]> {
  const response = await fetch(`${getApiBaseUrl()}/copywriter/platforms`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as CopywriterPlatform[];
}

export async function fetchCopywriterStyles(): Promise<CopywriterStyle[]> {
  const response = await fetch(`${getApiBaseUrl()}/copywriter/styles`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as CopywriterStyle[];
}

export async function fetchProductVersions(
  productId: string,
): Promise<CopywriterProductVersionsResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/products/${encodeURIComponent(productId)}/versions`,
    {
      method: "GET",
      credentials: "include",
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as CopywriterProductVersionsResponse;
}

export async function generateCopywriter(payload: {
  productId: string;
  version?: string | null;
  range?: string;
  start?: string | null;
  end?: string | null;
  platform: string;
  adTypeId?: string | null;
  style: string;
  nVariants?: number;
  featuresText: string;
  generateAdCopy: boolean;
  generateIdealDesc: boolean;
  forceRegenProfile?: boolean;
}): Promise<CopywriterGenerateResponse> {
  const response = await fetch(`${getApiBaseUrl()}/copywriter/generate`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      product_id: payload.productId,
      version: payload.version ?? null,
      range: payload.range ?? "all",
      start: payload.start ?? null,
      end: payload.end ?? null,
      platform: payload.platform,
      ad_type_id: payload.adTypeId ?? null,
      style: payload.style,
      n_variants: payload.nVariants ?? 1,
      features_text: payload.featuresText,
      generate_ad_copy: payload.generateAdCopy,
      generate_ideal_desc: payload.generateIdealDesc,
      force_regen_profile: payload.forceRegenProfile ?? false,
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as CopywriterGenerateResponse;
}

export async function createBillingCheckout(
  opts: { planKey?: string; period?: string } = {},
): Promise<BillingCheckoutResponse> {
  const response = await fetch(`${getApiBaseUrl()}/billing/checkout`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      success_url: typeof window !== "undefined" ? `${window.location.origin}/payment/success?plan=${opts.planKey ?? "pro"}` : "",
      plan_key: opts.planKey ?? "pro",
      period: opts.period ?? "monthly",
    }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as BillingCheckoutResponse;
}

export async function fetchTaxonomyCategories(locale?: string): Promise<TaxonomyCategoriesResponse> {
  const localeParam = locale ? `?locale=${encodeURIComponent(locale)}` : "";
  const response = await fetch(`${getApiBaseUrl()}/taxonomy/categories${localeParam}`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as TaxonomyCategoriesResponse;
}

export async function probeSubCategory(name: string): Promise<SubCategoryProbeResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/taxonomy/sub_category?name=${encodeURIComponent(name)}`,
    {
      method: "GET",
      credentials: "include",
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as SubCategoryProbeResponse;
}

// V5-T3: Smart Push Settings API

export async function fetchSmartPushSettings(): Promise<SmartPushSettingsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/settings/smart-push`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as SmartPushSettingsResponse;
}

export async function saveSmartPushSettings(
  payload: SmartPushSettingsResponse,
): Promise<SmartPushSettingsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/settings/smart-push`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as SmartPushSettingsResponse;
}

export async function submitFeedback(
  payload: FeedbackCreatePayload,
): Promise<FeedbackResponse> {
  const response = await fetch(`${getApiBaseUrl()}/feedback`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      feedback_type: payload.feedback_type,
      mood: payload.mood,
      message: payload.message || null,
      page_path: payload.page_path,
      user_agent: payload.user_agent || null,
      metadata: payload.metadata || {},
    }),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as FeedbackResponse;
}

// V5-T1: ASIN Watchlist API

export async function fetchAsinWatchlist(): Promise<AsinWatchlistResponse> {
  const response = await fetch(`${getApiBaseUrl()}/asin-watchlist`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as AsinWatchlistResponse;
}

export async function addAsinWatchlist(
  payload: AsinWatchlistCreatePayload,
): Promise<AsinWatchlistItem[]> {
  const response = await fetch(`${getApiBaseUrl()}/asin-watchlist`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as AsinWatchlistItem[];
}

export async function updateAsinWatchlistItem(
  itemId: number,
  payload: AsinWatchlistUpdatePayload,
): Promise<AsinWatchlistItem> {
  const response = await fetch(`${getApiBaseUrl()}/asin-watchlist/${itemId}`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as AsinWatchlistItem;
}

export async function deleteAsinWatchlistItem(itemId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/asin-watchlist/${itemId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
}

export async function deleteSession(sessionId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/analysis/sessions/${sessionId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
}

export async function fetchProductList(): Promise<import("./types").ProductsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/products`, {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return parseJsonBody<import("./types").ProductsResponse>(response);
}

export async function triggerAsinFetchNow(
  itemId: number,
): Promise<{ job_id: string; message: string }> {
  const response = await fetch(`${getApiBaseUrl()}/asin-watchlist/${itemId}/fetch-now`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return (await response.json()) as { job_id: string; message: string };
}

export async function translateModule(params: {
  sessionId: number;
  moduleKey: string;
  content: Record<string, unknown>;
  targetLang?: string;
}): Promise<{ translated: Record<string, unknown> }> {
  const response = await fetch(`${getApiBaseUrl()}/translate/module`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: params.sessionId,
      module_key: params.moduleKey,
      content: params.content,
      target_lang: params.targetLang || "zh",
    }),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return parseJsonBody<{ translated: Record<string, unknown> }>(response);
}

export async function exportModuleXlsx(sessionId: number, moduleKey: string, locale?: string): Promise<Blob> {
  const localeParam = locale ? `&locale=${encodeURIComponent(locale)}` : "";
  const response = await fetch(
    `${getApiBaseUrl()}/analysis/sessions/${sessionId}/export?module=${encodeURIComponent(moduleKey)}${localeParam}`,
    { credentials: "include" },
  );
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.blob();
}

export async function exportFullXlsx(sessionId: number): Promise<Blob> {
  const response = await fetch(
    `${getApiBaseUrl()}/analysis/sessions/${sessionId}/export/full`,
    { credentials: "include" },
  );
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.blob();
}

export type ProductCreatePayload = {
  parent_product_id: string;
  name?: string;
  platform?: string;
  category?: string;
  lifecycle_stage?: string;
  current_version?: string;
  core_selling_points?: string;
  main_competitors?: string;
  owner_role?: string;
  production_cycle_days?: number;
};

export type ProductUpdatePayload = Partial<ProductCreatePayload>;

export async function createProduct(payload: ProductCreatePayload): Promise<{ id: number }> {
  const response = await fetch(`${getApiBaseUrl()}/products`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}

export async function updateProduct(productId: number, payload: ProductUpdatePayload): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/products/${productId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
}

export async function deleteProduct(productId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/products/${productId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
}

export async function deleteVariant(productId: number, variantId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/products/${productId}/variants/${variantId}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
}

export async function moveVariant(
  productId: number,
  variantId: number,
  targetProductId: number,
): Promise<{ success: boolean; message?: string }> {
  const response = await fetch(
    `${getApiBaseUrl()}/products/${productId}/variants/${variantId}/move`,
    {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_product_id: targetProductId }),
    },
  );
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}

export async function checkAsinAvailability(
  asin: string,
  platform = "amazon",
  marketplace = "us",
): Promise<{ asin: string; platform: string; available: boolean; suggestion?: string }> {
  const search = new URLSearchParams({ asin, platform, marketplace });
  const response = await fetch(
    `${getApiBaseUrl()}/reviews/check-asin-availability?${search.toString()}`,
    { credentials: "include" },
  );
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}

export async function fetchDownloads(): Promise<import("./types").DownloadRecord[]> {
  const response = await fetch(`${getApiBaseUrl()}/downloads`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}

export async function recordDownload(name: string, source: string): Promise<void> {
  fetch(`${getApiBaseUrl()}/downloads`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, source, status: "completed" }),
  }).catch(() => {});
}

// V4-出海-M3.2: 数据主权 API (导出/更正/删除自己的账号)
export async function exportMyData(): Promise<import("./types").MeExportPayload> {
  const response = await fetch(`${getApiBaseUrl()}/me/export`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}

export async function updateMyProfile(
  payload: import("./types").MeUpdatePayload,
): Promise<import("./types").MeExportUser> {
  const response = await fetch(`${getApiBaseUrl()}/me`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}

// V4-出海-M2.5: Terms Gate — 老用户补同意 Terms
export async function acceptTerms(
  termsVersion: string,
): Promise<{ ok: boolean; message: string }> {
  const response = await fetch(`${getApiBaseUrl()}/auth/accept-terms`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ terms_version: termsVersion }),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}

export async function deleteMyAccount(
  payload: import("./types").MeDeletePayload,
): Promise<{ ok: boolean; message: string }> {
  const response = await fetch(`${getApiBaseUrl()}/me`, {
    method: "DELETE",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw await parseError(response);
  }
  return response.json();
}
