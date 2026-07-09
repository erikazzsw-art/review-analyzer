"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import {
  addAsinWatchlist,
  deleteAsinWatchlistItem,
  fetchAsinWatchlist,
  triggerAsinFetchNow,
  updateAsinWatchlistItem,
} from "@/lib/api/browser";
import { track } from "@/lib/analytics";
import type { AsinWatchlistItem, AsinWatchlistResponse } from "@/lib/api/types";

const AMAZON_MARKETPLACES = [
  { value: "us", label: "US" },
  { value: "uk", label: "UK" },
  { value: "ca", label: "CA" },
  { value: "au", label: "AU" },
] as const;

const FREQUENCY_VALUES = ["daily", "weekly", "manual"] as const;

function statusBadge(status: AsinWatchlistItem["status"]) {
  if (status === "active") return "bg-[#e8f8f0] text-[#3d8b74]";
  return "bg-[#f5f5f5] text-[#888]";
}

export function AsinWatchlistPanel() {
  const t = useTranslations("upload.asinWatchlist");
  const [data, setData] = useState<AsinWatchlistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [addInput, setAddInput] = useState("");
  const [addPlatform, setAddPlatform] = useState<"amazon" | "aliexpress" | "ebay" | "walmart">("amazon");
  const [addMarketplace, setAddMarketplace] = useState("us");
  const [addFrequency, setAddFrequency] = useState<"daily" | "weekly" | "manual">("daily");
  const [submitting, setSubmitting] = useState(false);
  const [fetchingId, setFetchingId] = useState<number | null>(null);

  function relativeTime(dateStr: string | null): string {
    if (!dateStr) return t("neverFetched");
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return t("minutesAgo", { minutes: mins });
    const hours = Math.floor(mins / 60);
    if (hours < 24) return t("hoursAgo", { hours });
    return t("daysAgo", { days: Math.floor(hours / 24) });
  }

  const loadData = useCallback(async () => {
    try {
      const res = await fetchAsinWatchlist();
      setData(res);
      setError("");
    } catch (err) {
      setError((err as { message?: string }).message || t("loadFail"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function validateInput(): string[] {
    const raw = addInput.split(/[\n,;]/).map((s) => s.trim()).filter(Boolean);
    if (addPlatform === "amazon") {
      return raw
        .map((s) => s.toUpperCase())
        .filter((s) => s.length === 10 && /^[A-Z0-9]{10}$/.test(s));
    }
    if (addPlatform === "aliexpress") {
      return raw.filter((s) => /^\d{8,16}$/.test(s));
    }
    if (addPlatform === "ebay") {
      return raw.filter((s) => /^\d{9,15}$/.test(s));
    }
    if (addPlatform === "walmart") {
      return raw.filter((s) => /^[A-Za-z0-9]{6,13}$/.test(s));
    }
    return raw;
  }

  async function handleAdd() {
    const productIds = validateInput();
    if (productIds.length === 0) {
      const hintKey =
        addPlatform === "amazon" ? "invalidAmazon" :
        addPlatform === "aliexpress" ? "invalidAliexpress" :
        addPlatform === "ebay" ? "invalidEbay" :
        addPlatform === "walmart" ? "invalidWalmart" :
        "invalidGeneric";
      setError(t(hintKey));
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const marketplaceMap: Record<string, string> = {
        amazon: addMarketplace,
        aliexpress: "global",
        ebay: "global",
        walmart: "us",
      };
      await addAsinWatchlist({
        platform: addPlatform,
        product_ids: productIds,
        marketplace: marketplaceMap[addPlatform] || "global",
        fetch_frequency: addFrequency,
      });
      track("asin_watchlist_add", { count: productIds.length, platform: addPlatform });
      setAddInput("");
      await loadData();
    } catch (err) {
      setError((err as { message?: string }).message || t("addFail"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleFetchNow(item: AsinWatchlistItem) {
    setFetchingId(item.id);
    try {
      await triggerAsinFetchNow(item.id);
      track("asin_watchlist_fetch_now", { asin: item.asin });
      await loadData();
    } catch (err) {
      setError((err as { message?: string }).message || t("fetchNowFail"));
    } finally {
      setFetchingId(null);
    }
  }

  async function handleTogglePause(item: AsinWatchlistItem) {
    const newStatus = item.status === "active" ? "paused" : "active";
    try {
      await updateAsinWatchlistItem(item.id, { status: newStatus });
      await loadData();
    } catch (err) {
      setError((err as { message?: string }).message || t("updateFail"));
    }
  }

  async function handleDelete(item: AsinWatchlistItem) {
    try {
      await deleteAsinWatchlistItem(item.id);
      track("asin_watchlist_delete", { asin: item.asin });
      await loadData();
    } catch (err) {
      setError((err as { message?: string }).message || t("deleteFail"));
    }
  }

  async function handleFrequencyChange(item: AsinWatchlistItem, freq: string) {
    try {
      await updateAsinWatchlistItem(item.id, {
        fetch_frequency: freq as "daily" | "weekly" | "manual",
      });
      await loadData();
    } catch (err) {
      setError((err as { message?: string }).message || t("updateFail"));
    }
  }

  if (loading) {
    return <div className="py-8 text-center text-sm text-soft">{t("loading")}</div>;
  }

  const addPlaceholderKey =
    addPlatform === "amazon" ? "amazonPlaceholder" :
    addPlatform === "ebay" ? "ebayPlaceholder" :
    addPlatform === "walmart" ? "walmartPlaceholder" :
    "aliexpressPlaceholder";

  return (
    <div className="space-y-6">
      {/* Add form */}
      <div className="rounded-card border border-line bg-white p-5 space-y-4">
        <h3 className="text-sm font-semibold text-ink">{t("addTitle")}</h3>

        {/* Platform selector */}
        <div className="flex flex-wrap gap-2">
          {(["amazon", "aliexpress", "ebay", "walmart"] as const).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setAddPlatform(p)}
              className={`rounded-pill px-4 py-1.5 text-sm font-medium transition ${
                addPlatform === p
                  ? "bg-ink text-white"
                  : "bg-[#f5f5f5] text-soft hover:bg-[#eee]"
              }`}
            >
              {p === "amazon" ? "Amazon" : p === "aliexpress" ? "AliExpress" : p === "ebay" ? "eBay" : "Walmart"}
            </button>
          ))}
        </div>

        <div className="grid gap-3 md:grid-cols-4">
          <div className="md:col-span-2">
            <textarea
              value={addInput}
              onChange={(e) => setAddInput(e.target.value)}
              rows={2}
              className="w-full rounded-card border border-line bg-white px-3 py-2 text-sm font-mono outline-none transition focus:border-[#f36f8f] resize-none"
              placeholder={t(addPlaceholderKey)}
            />
          </div>
          <div className="space-y-2">
            {addPlatform === "amazon" && (
              <select
                value={addMarketplace}
                onChange={(e) => setAddMarketplace(e.target.value)}
                className="w-full rounded-card border border-line bg-white px-3 py-2 text-sm"
              >
                {AMAZON_MARKETPLACES.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            )}
            <select
              value={addFrequency}
              onChange={(e) => setAddFrequency(e.target.value as typeof addFrequency)}
              className="w-full rounded-card border border-line bg-white px-3 py-2 text-sm"
            >
              {FREQUENCY_VALUES.map((value) => (
                <option key={value} value={value}>{t(`frequencyLabel.${value}`)}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              type="button"
              onClick={handleAdd}
              disabled={submitting || !addInput.trim()}
              className="w-full rounded-pill bg-ink px-4 py-2 text-sm font-semibold text-white shadow-card transition disabled:opacity-60"
            >
              {submitting ? t("addBtnLoading") : t("addBtn")}
            </button>
          </div>
        </div>
        {data && (
          <p className="text-xs text-soft">
            {t("quotaLabel", { used: data.quota_used, limit: data.quota_limit })}
          </p>
        )}
      </div>

      {error && (
        <div className="rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm text-[#b44655]">
          {error}
        </div>
      )}

      {/* Watchlist table */}
      {data && data.items.length > 0 && (
        <div className="rounded-card border border-line bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#fafafa] border-b border-line">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-ink">{t("columnPlatform")}</th>
                <th className="px-4 py-3 text-left font-semibold text-ink">{t("columnProductCode")}</th>
                <th className="px-4 py-3 text-left font-semibold text-ink">{t("columnProductName")}</th>
                <th className="px-4 py-3 text-center font-semibold text-ink">{t("columnMarketplace")}</th>
                <th className="px-4 py-3 text-center font-semibold text-ink">{t("columnFrequency")}</th>
                <th className="px-4 py-3 text-center font-semibold text-ink">{t("columnStatus")}</th>
                <th className="px-4 py-3 text-center font-semibold text-ink">{t("columnLastFetched")}</th>
                <th className="px-4 py-3 text-center font-semibold text-ink">{t("columnNewReviews")}</th>
                <th className="px-4 py-3 text-right font-semibold text-ink">{t("columnActions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {data.items.map((item) => (
                <tr key={item.id} className="hover:bg-[#fafafa] transition">
                  <td className="px-4 py-3 text-xs">
                    <span className={`rounded-pill px-2 py-0.5 font-medium ${
                      item.platform === "amazon"
                        ? "bg-[#fff4e5] text-[#b87333]"
                        : "bg-[#ffe8e8] text-[#c45050]"
                    }`}>
                      {item.platform === "amazon" ? "Amazon" : "AliExpress"}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{item.asin}</td>
                  <td className="px-4 py-3 text-soft max-w-[160px] truncate">
                    {item.product_name || "—"}
                  </td>
                  <td className="px-4 py-3 text-center uppercase text-xs">
                    {item.marketplace === "global" ? "—" : item.marketplace}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <select
                      value={item.fetch_frequency}
                      onChange={(e) => handleFrequencyChange(item, e.target.value)}
                      className="rounded border border-line px-2 py-1 text-xs bg-white"
                    >
                      {FREQUENCY_VALUES.map((value) => (
                        <option key={value} value={value}>{t(`frequencyLabel.${value}`)}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`rounded-pill px-2 py-0.5 text-xs font-bold ${statusBadge(item.status)}`}>
                      {item.status === "active" ? t("statusActive") : t("statusPaused")}
                    </span>
                    {item.hint_message && (
                      <p className="text-[10px] text-[#b08d57] mt-0.5">{item.hint_message}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center text-xs text-soft">
                    {relativeTime(item.last_fetched_at)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {item.new_review_count > 0 ? (
                      <span className="text-[#3d8b74] font-semibold">+{item.new_review_count}</span>
                    ) : (
                      <span className="text-soft">0</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right space-x-1">
                    <button
                      type="button"
                      onClick={() => handleFetchNow(item)}
                      disabled={fetchingId === item.id}
                      className="rounded px-2 py-1 text-xs bg-[#eef6ff] text-[#4a7dc7] hover:bg-[#dbeafe] transition disabled:opacity-50"
                      title={t("fetchNowTooltip")}
                    >
                      {fetchingId === item.id ? t("fetchNowBtnLoading") : t("fetchNowBtn")}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleTogglePause(item)}
                      className="rounded px-2 py-1 text-xs bg-[#f5f5f5] text-[#666] hover:bg-[#eee] transition"
                    >
                      {item.status === "active" ? t("pauseBtn") : t("resumeBtn")}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(item)}
                      className="rounded px-2 py-1 text-xs bg-[#fdeaea] text-[#c45863] hover:bg-[#fdd] transition"
                    >
                      {t("deleteBtn")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.items.length === 0 && (
        <div className="py-8 text-center text-sm text-soft">
          {t("emptyState")}
        </div>
      )}
    </div>
  );
}
