"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
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

export default function GoldenSetPage() {
  const router = useRouter();
  const [stats, setStats] = useState<AccuracyStat[]>([]);
  const [entries, setEntries] = useState<GoldenEntry[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const [filterAspect, setFilterAspect] = useState<string | null>(null);
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    fetch("/api/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d?.is_admin) {
          setAuthorized(true);
        } else {
          router.replace("/workspace");
        }
      })
      .catch(() => router.replace("/workspace"));
  }, [router]);

  const fetchData = useCallback(async () => {
    if (!authorized) return;
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
  }, [filterAspect, authorized]);

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
        setUploadResult(`上传成功：${data.count} 条记录`);
        fetchData();
      } else {
        setUploadResult(`上传失败：${JSON.stringify(data)}`);
      }
    } catch (err) {
      setUploadResult(`上传异常：${String(err)}`);
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

  if (!authorized) return null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-bold text-ink">标签校准（Golden Set）</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        上传人工标注数据，追踪各标签准确率，精选 few-shot 示例提升模型标签质量
      </p>

      {/* Summary Cards */}
      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">总条目</p>
          <p className="text-2xl font-bold">{summary?.total_entries ?? "—"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">覆盖标签数</p>
          <p className="text-2xl font-bold">{summary?.aspect_count ?? "—"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">整体准确率</p>
          <p className="text-2xl font-bold">
            {summary?.overall_accuracy_pct != null
              ? `${summary.overall_accuracy_pct}%`
              : "—"}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground">正确标注</p>
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
            {uploading ? "上传中…" : "上传 CSV 标注文件"}
          </span>
        </label>
        <span className="text-xs text-muted-foreground">
          表头：序号, 英文原文, 原标签, 标签正确？, 原因
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
          <h2 className="text-lg font-semibold text-ink">各标签准确率</h2>
          <div className="mt-3 rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>标签</TableHead>
                  <TableHead className="text-right">总数</TableHead>
                  <TableHead className="text-right">正确</TableHead>
                  <TableHead className="text-right">错误</TableHead>
                  <TableHead className="text-right">准确率</TableHead>
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
                        {filterAspect === s.aspect_key ? "清除筛选" : "查看"}
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
            标注记录
            {filterAspect && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                （筛选：{filterAspect}）
              </span>
            )}
          </h2>
          <span className="text-sm text-muted-foreground">
            共 {entries.length} 条
          </span>
        </div>
        {entries.length > 0 ? (
          <div className="mt-3 rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[40%]">评论原文</TableHead>
                  <TableHead>标签</TableHead>
                  <TableHead>正确？</TableHead>
                  <TableHead>原因</TableHead>
                  <TableHead>Few-shot</TableHead>
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
                        <Badge variant="default">正确</Badge>
                      ) : (
                        <Badge variant="destructive">错误</Badge>
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
                        {entry.use_as_fewshot ? "已选" : "选为示例"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">
            暂无数据，请上传 CSV 标注文件
          </p>
        )}
      </div>
    </div>
  );
}