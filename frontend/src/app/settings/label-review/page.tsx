"use client";

import { useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ProposalItem = {
  id: number;
  label_key: string;
  action_type: string;
  proposal_data: Record<string, unknown>;
  evidence_summary: string;
  proposal_status: string;
  reviewer_note: string;
  reviewed_by: string;
  reviewed_at: string;
  created_at: string;
};

const ACTION_LABELS: Record<string, string> = {
  scope_adjust: "Scope Adjustment",
  alias_merge: "Alias Merge",
  blocked_rule: "Blocked Context Rule",
  negative_example: "Negative Example",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  applied: "bg-blue-100 text-blue-800",
};

// ---------------------------------------------------------------------------
// API helpers (inline — decision o: minimal page, no new client module)
// ---------------------------------------------------------------------------

async function fetchProposals(
  statusFilter: string = "pending"
): Promise<ProposalItem[]> {
  const res = await fetch(`/api/settings/label-review/proposals?status=${statusFilter}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to fetch proposals: ${res.status}`);
  const data = await res.json();
  return data.proposals || [];
}

async function reviewProposal(
  proposalId: number,
  action: "approve" | "reject" | "merge",
  note: string = ""
): Promise<{ success: boolean; message: string; validation_output?: string }> {
  const res = await fetch("/api/settings/label-review/review", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ proposal_id: proposalId, action, reviewer_note: note }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function LabelReviewPage() {
  const [proposals, setProposals] = useState<ProposalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [actionMessages, setActionMessages] = useState<Record<number, string>>({});
  const [reviewNote, setReviewNote] = useState("");

  const load = async (status: string) => {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchProposals(status);
      setProposals(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load proposals");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(statusFilter);
  }, [statusFilter]);

  const handleAction = async (id: number, action: "approve" | "reject" | "merge") => {
    setActionMessages((prev) => ({ ...prev, [id]: `${action}...` }));
    try {
      const result = await reviewProposal(id, action, reviewNote);
      setActionMessages((prev) => ({
        ...prev,
        [id]: result.message,
      }));
      // Reload after a short delay
      setTimeout(() => load(statusFilter), 1000);
    } catch (err) {
      setActionMessages((prev) => ({
        ...prev,
        [id]: `Error: ${err instanceof Error ? err.message : "Unknown"}`,
      }));
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-2">Label Registry Review</h1>
      <p className="text-sm text-gray-500 mb-6">
        Internal page — review and merge label registry proposals.
      </p>

      {/* Status filter */}
      <div className="flex gap-2 mb-6">
        {["pending", "approved", "rejected", "applied"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded text-sm font-medium transition ${
              statusFilter === s
                ? "bg-gray-800 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Review note input */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Reviewer Note
        </label>
        <input
          type="text"
          value={reviewNote}
          onChange={(e) => setReviewNote(e.target.value)}
          placeholder="Optional note for approve/reject/merge..."
          className="w-full max-w-md px-3 py-2 border border-gray-300 rounded text-sm"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && <p className="text-sm text-gray-500">Loading proposals...</p>}

      {/* Proposal list */}
      {!loading && proposals.length === 0 && (
        <p className="text-sm text-gray-500">No {statusFilter} proposals found.</p>
      )}

      <div className="space-y-4">
        {proposals.map((p) => (
          <div
            key={p.id}
            className="border border-gray-200 rounded-lg p-4 bg-white shadow-sm"
          >
            <div className="flex items-start justify-between mb-2">
              <div>
                <span className="font-mono text-sm font-semibold text-gray-800">
                  {p.label_key}
                </span>
                <span className="ml-2 text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                  {ACTION_LABELS[p.action_type] || p.action_type}
                </span>
                <span
                  className={`ml-2 text-xs px-2 py-0.5 rounded ${
                    STATUS_COLORS[p.proposal_status] || "bg-gray-100 text-gray-600"
                  }`}
                >
                  {p.proposal_status}
                </span>
              </div>
              <span className="text-xs text-gray-400">{p.created_at?.slice(0, 10)}</span>
            </div>

            {/* Proposal data */}
            <pre className="text-xs bg-gray-50 p-2 rounded mb-2 overflow-x-auto max-h-32">
              {JSON.stringify(p.proposal_data, null, 2)}
            </pre>

            {p.evidence_summary && (
              <p className="text-xs text-gray-500 mb-2">{p.evidence_summary}</p>
            )}

            {p.reviewer_note && (
              <p className="text-xs text-gray-500 mb-2">
                Note: {p.reviewer_note}
              </p>
            )}

            {/* Actions (only for pending proposals) */}
            {p.proposal_status === "pending" && (
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => handleAction(p.id, "approve")}
                  className="px-3 py-1 text-xs font-medium rounded bg-green-600 text-white hover:bg-green-700 transition"
                >
                  Approve
                </button>
                <button
                  onClick={() => handleAction(p.id, "merge")}
                  className="px-3 py-1 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700 transition"
                >
                  Merge & Write YAML
                </button>
                <button
                  onClick={() => handleAction(p.id, "reject")}
                  className="px-3 py-1 text-xs font-medium rounded bg-red-600 text-white hover:bg-red-700 transition"
                >
                  Reject
                </button>
              </div>
            )}

            {/* Action result message */}
            {actionMessages[p.id] && (
              <p className="mt-2 text-xs text-gray-600">{actionMessages[p.id]}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
