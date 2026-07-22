import { cookies } from "next/headers";

import type {
  ActionItemsResponse,
  CopywriterPlatform,
  AnalysisCompareResponse,
  AnalysisHistoryResponse,
  AnalysisResultsResponse,
  AnalysisSessionResultsResponse,
  CompareLatestResponse,
  QaProduct,
  ProductsResponse,
  ProductSearchResponse,
  SettingsResponse,
  ReviewTrackersResponse,
  WorkspaceRole,
  WorkspaceSummary,
} from "@/lib/api/types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

type ApiError = {
  status: number;
  message: string;
};

function getApiBaseUrl(): string {
  return (
    process.env.API_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
    DEFAULT_API_BASE_URL
  );
}

async function buildCookieHeader(): Promise<string> {
  const store = await cookies();
  return store
    .getAll()
    .map((item) => `${item.name}=${item.value}`)
    .join("; ");
}

async function apiFetch<T>(path: string): Promise<T> {
  const cookieHeader = await buildCookieHeader();
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
    cache: "no-store",
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {}

    throw {
      status: response.status,
      message,
    } satisfies ApiError;
  }

  return (await response.json()) as T;
}

export async function getWorkspaceSummary(
  role: WorkspaceRole = "运营",
): Promise<WorkspaceSummary> {
  const search = new URLSearchParams({ role, lang: "zh" });
  return apiFetch<WorkspaceSummary>(`/workspace/summary?${search.toString()}`);
}

export async function getProducts(): Promise<ProductsResponse> {
  return apiFetch<ProductsResponse>("/products");
}

export async function getProductDetail(productId: number): Promise<{
  product: Record<string, unknown>;
  variants: Record<string, unknown>[];
}> {
  return apiFetch(`/products/${productId}/detail`);
}

export async function getQaProducts(): Promise<QaProduct[]> {
  return apiFetch<QaProduct[]>("/qa/products");
}

export async function getActionItems(): Promise<ActionItemsResponse> {
  return apiFetch<ActionItemsResponse>("/actions");
}

export async function getReviewTrackers(status?: string): Promise<ReviewTrackersResponse> {
  const search = status ? `?${new URLSearchParams({ tracker_status: status }).toString()}` : "";
  return apiFetch<ReviewTrackersResponse>(`/actions/trackers${search}`);
}

export async function getAnalysisSessionResults(
  sessionId: number,
): Promise<AnalysisSessionResultsResponse> {
  return apiFetch<AnalysisSessionResultsResponse>(`/analysis/sessions/${sessionId}/results`);
}

export async function getAnalysisResults(params: {
  productId: string;
  variantAsin?: string | null;
  range?: string;
  start?: string | null;
  end?: string | null;
  sessionId?: number | null;
  version?: string | null;
}): Promise<AnalysisResultsResponse> {
  const search = new URLSearchParams();
  search.set("product_id", params.productId);
  if (params.variantAsin) {
    search.set("variant_asin", params.variantAsin);
  }
  if (params.range) {
    search.set("range", params.range);
  }
  if (params.start) {
    search.set("start", params.start);
  }
  if (params.end) {
    search.set("end", params.end);
  }
  if (params.sessionId) {
    search.set("session_id", String(params.sessionId));
  }
  if (params.version) {
    search.set("version", params.version);
  }
  return apiFetch<AnalysisResultsResponse>(`/analysis/results?${search.toString()}`);
}

export async function searchProductsServer(
  q: string,
  limit = 20,
): Promise<ProductSearchResponse> {
  const search = new URLSearchParams({ q, limit: String(limit) });
  return apiFetch<ProductSearchResponse>(`/products/search?${search.toString()}`);
}

export async function getAnalysisCompare(params?: {
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
  return apiFetch<AnalysisCompareResponse>(`/analysis/compare${query ? `?${query}` : ""}`);
}

export async function getAnalysisHistory(productId?: string): Promise<AnalysisHistoryResponse> {
  const search = productId ? `?${new URLSearchParams({ product_id: productId }).toString()}` : "";
  return apiFetch<AnalysisHistoryResponse>(`/analysis/history${search}`);
}

export async function getAnalysisSessionHistory(sessionId: number): Promise<AnalysisHistoryResponse> {
  return apiFetch<AnalysisHistoryResponse>(`/analysis/sessions/${sessionId}/history`);
}

export async function getSettings(): Promise<SettingsResponse> {
  return apiFetch<SettingsResponse>("/settings");
}

export async function getCopywriterPlatforms(): Promise<CopywriterPlatform[]> {
  return apiFetch<CopywriterPlatform[]>("/copywriter/platforms");
}

export type QuotaItem = {
  dimension: string;
  used?: number;
  limit: number;
  remaining?: number;
  unlimited?: boolean;
  period: string;
  plan: string;
  unit?: string;
  error?: string;
};

export async function getQuota(): Promise<QuotaItem[]> {
  return apiFetch<QuotaItem[]>("/quota");
}

export async function getCompareLatest(): Promise<CompareLatestResponse | null> {
  const cookieHeader = await buildCookieHeader();
  const response = await fetch(`${getApiBaseUrl()}/compare/latest`, {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
    cache: "no-store",
  });
  if (!response.ok) {
    return null;
  }
  const body = await response.json();
  if (!body || !body.dataset) {
    return null;
  }
  return body as CompareLatestResponse;
}

export function isApiError(value: unknown): value is ApiError {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<ApiError>;
  return typeof candidate.status === "number" && typeof candidate.message === "string";
}
