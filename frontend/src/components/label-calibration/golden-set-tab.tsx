"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type AccuracyStat = {
  aspect_key: string;
  total: number;
  correct_count: number;
  incorrect_count: number;
  accuracy_pct: number | null;
};

type GoldenEntry = {
  id: number;
  comment_text: string;
  aspect_key: string;
  is_correct: boolean;
  reason: string | null;
  correct_tag: string | null;
  sub_category: string;
  source: string;
  use_as_fewshot: boolean;
  batch_id: string | null;
  created_at: string;
};

type Summary = {
  total_entries: number;
  total_correct: number;
  overall_accuracy_pct: number | null;
  aspect_count: number;
};

export default function GoldenSetTab() {
  const t = useTranslations("settings.goldenSet");
  const [stats, setStats] = useState<AccuracyStat[]>([]);
  const [entries, setEntries] = useState<GoldenEntry[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [filterAspect, setFilterAspect] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    const [statsRes, entriesRes, summaryRes] = await Promise.all([
      fetch("/api/golden-set/stats", { credentials: "include" }),
      fetch(
        `/api/golden-set/entries?limit=200${filterAspect ? `&aspect_key=${filterAspect}` : ""}`,
        { credentials: "include" }
      ),
      fetch("/api/golden-set/summary", { credentials: "include" }),
    ]);
    if (statsRes.ok) setStats(await statsRes.json());
    if (entriesRes.ok) setEntries(await entriesRes.json());
    if (summaryRes.ok) setSummary(await summaryRes.json());
  }, [filterAspect]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("/api/golden-set/upload-csv?sub_category=家具家居", {
        method: "POST",
        credentials: "include",
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadResult(t("uploadSuccess", { count: data.count }));
        fetchData();
      } else {
        setUploadResult(t("uploadFail", { detail: JSON.stringify(data) }));
      }
    } catch (err) {
      setUploadResult(t("uploadException", { detail: String(err) }));
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const toggleFewshot = async (id: number, current: boolean) => {
    await fetch(`/api/golden-set/${id}/fewshot?use_as_fewshot=${!current}`, {
      method: "PATCH",
      credentials: "include",
    });
    setEntries((prev) =>
      prev.map((e) => (e.id === id ? { ...e, use_as_fewshot: !current } : e))
    );
  };

  return (
    <div>
      <p className="mt-1 text-sm text-muted-foreground">
        {t("description")}
      </p>

      {/* Summary Cards */}
      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">{t("totalEntries")}</p>
          <p className="text-2xl font-bold">{summary?.total_entries ?? "—"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">{t("aspectCount")}</p>
          <p className="text-2xl font-bold">{summary?.aspect_count ?? "—"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">{t("overallAccuracy")}</p>
          <p className="text-2xl font-bold">
            {summary?.overall_accuracy_pct != null
              ? `${summary.overall_accuracy_pct}%`
              : "—"}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">{t("totalCorrect")}</p>
          <p className="text-2xl font-bold">{summary?.total_correct ?? "—"}</p>
        </Card>
      </div>

      {/* Upload Section */}
      <div className="mt-6 flex items-center gap-4">
        <label className="cursor-pointer">
          <input
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleFileUpload}
            disabled={uploading}
          />
          <span className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90">
            {uploading ? t("uploadBtnLoading") : t("uploadBtn")}
          </span>
        </label>
        <span className="text-xs text-muted-foreground">
          {t("uploadHint")}
        </span>
        {uploadResult && (
          <span className="text-sm font-medium text-emerald-600">
            {uploadResult}
          </span>
        )}
      </div>

      {/* Accuracy Stats Table */}
      {stats.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-ink">{t("accuracyTitle")}</h2>
          <div className="mt-3 rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("columnTag")}</TableHead>
                  <TableHead className="text-right">{t("columnTotal")}</TableHead>
                  <TableHead className="text-right">{t("columnCorrect")}</TableHead>
                  <TableHead className="text-right">{t("columnIncorrect")}</TableHead>
                  <TableHead className="text-right">{t("columnAccuracy")}</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stats.map((s) => (
                  <TableRow key={s.aspect_key}>
                    <TableCell className="font-medium">{s.aspect_key}</TableCell>
                    <TableCell className="text-right">{s.total}</TableCell>
                    <TableCell className="text-right text-emerald-600">
                      {s.correct_count}
                    </TableCell>
                    <TableCell className="text-right text-red-500">
                      {s.incorrect_count}
                    </TableCell>
                    <TableCell className="text-right">
                      {s.accuracy_pct != null ? (
                        <Badge
                          variant={s.accuracy_pct >= 80 ? "default" : "destructive"}
                        >
                          {s.accuracy_pct}%
                        </Badge>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setFilterAspect(
                            filterAspect === s.aspect_key ? null : s.aspect_key
                          )
                        }
                      >
                        {filterAspect === s.aspect_key ? t("clearFilter") : t("viewDetail")}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* Entries Table */}
      <div className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink">
            {t("entriesTitle")}
            {filterAspect && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {t("filterLabel", { aspect: filterAspect })}
              </span>
            )}
          </h2>
          <span className="text-sm text-muted-foreground">
            {t("entriesCount", { count: entries.length })}
          </span>
        </div>
        {entries.length > 0 ? (
          <div className="mt-3 rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40%]">{t("colComment")}</TableHead>
                  <TableHead>{t("colTag")}</TableHead>
                  <TableHead>{t("colCorrect")}</TableHead>
                  <TableHead>{t("colReason")}</TableHead>
                  <TableHead>{t("colFewshot")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="max-w-xs truncate text-xs">
                      {entry.comment_text}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{entry.aspect_key}</Badge>
                    </TableCell>
                    <TableCell>
                      {entry.is_correct ? (
                        <Badge variant="default">{t("correctBadge")}</Badge>
                      ) : (
                        <Badge variant="destructive">{t("incorrectBadge")}</Badge>
                      )}
                    </TableCell>
                    <TableCell className="max-w-[160px] truncate text-xs text-muted-foreground">
                      {entry.reason || "—"}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant={entry.use_as_fewshot ? "default" : "ghost"}
                        size="sm"
                        onClick={() => toggleFewshot(entry.id, entry.use_as_fewshot)}
                      >
                        {entry.use_as_fewshot ? t("fewshotSelected") : t("fewshotSelect")}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">
            {t("emptyState")}
          </p>
        )}
      </div>
    </div>
  );
}
