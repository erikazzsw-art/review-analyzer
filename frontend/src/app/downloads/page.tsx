"use client";

import { useEffect, useState } from "react";
import { FileDown } from "lucide-react";

import { fetchDownloads } from "@/lib/api/browser";
import type { DownloadRecord } from "@/lib/api/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    completed: { label: "已完成", cls: "bg-emerald-50 text-emerald-700" },
    processing: { label: "处理中", cls: "bg-blue-50 text-blue-700" },
    failed: { label: "失败", cls: "bg-red-50 text-red-700" },
  };
  const info = map[status] ?? { label: status, cls: "bg-gray-50 text-gray-700" };
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${info.cls}`}>
      {info.label}
    </span>
  );
}

export default function DownloadsPage() {
  const [records, setRecords] = useState<DownloadRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDownloads()
      .then(setRecords)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-xl font-bold text-ink">我的导出</h1>
      <p className="mt-1 text-sm text-soft">所有导出记录都会保存在这里</p>

      <div className="mt-6 rounded-xl border border-line bg-white shadow-card">
        {loading ? (
          <div className="flex items-center justify-center py-20 text-sm text-soft">
            加载中...
          </div>
        ) : records.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-soft">
            <FileDown className="mb-3 h-10 w-10 opacity-30" />
            <p className="text-sm">暂无数据</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-b border-line">
                <TableHead className="pl-5 text-xs font-semibold text-soft">名称</TableHead>
                <TableHead className="text-xs font-semibold text-soft">来源</TableHead>
                <TableHead className="text-xs font-semibold text-soft">操作时间</TableHead>
                <TableHead className="text-xs font-semibold text-soft">状态</TableHead>
                <TableHead className="pr-5 text-xs font-semibold text-soft">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {records.map((r) => (
                <TableRow key={r.id} className="border-b border-line last:border-0">
                  <TableCell className="pl-5 font-medium text-ink">{r.name}</TableCell>
                  <TableCell className="text-soft">{r.source}</TableCell>
                  <TableCell className="text-soft">
                    {new Date(r.created_at).toLocaleString("zh-CN")}
                  </TableCell>
                  <TableCell><StatusBadge status={r.status} /></TableCell>
                  <TableCell className="pr-5">
                    {r.file_url && r.status === "completed" ? (
                      <a
                        href={r.file_url}
                        download
                        className="text-sm font-medium text-rose hover:underline"
                      >
                        重新下载
                      </a>
                    ) : (
                      <span className="text-xs text-soft">—</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}
