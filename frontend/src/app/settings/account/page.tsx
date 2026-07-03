"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  deleteMyAccount,
  exportMyData,
  updateMyProfile,
} from "@/lib/api/browser";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Banner = { kind: "success" | "error"; text: string } | null;

export default function AccountSettingsPage() {
  const router = useRouter();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [saving, setSaving] = useState(false);

  const [exporting, setExporting] = useState(false);

  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const [deleting, setDeleting] = useState(false);

  const [banner, setBanner] = useState<Banner>(null);

  async function handleExport(): Promise<void> {
    setBanner(null);
    setExporting(true);
    try {
      const payload = await exportMyData();
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `clueai-data-export-user${payload.user.id}-${payload.exported_at.slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setBanner({ kind: "success", text: "数据已导出并触发下载。" });
    } catch (err) {
      setBanner({
        kind: "error",
        text: (err as { message?: string })?.message || "导出失败",
      });
    } finally {
      setExporting(false);
    }
  }

  async function handleUpdate(): Promise<void> {
    setBanner(null);
    if (!currentPassword) {
      setBanner({ kind: "error", text: "请输入当前密码以完成校验。" });
      return;
    }
    const payload: {
      current_password: string;
      username?: string;
      email?: string;
      new_password?: string;
    } = { current_password: currentPassword };
    if (newUsername.trim()) payload.username = newUsername.trim();
    if (newEmail.trim()) payload.email = newEmail.trim();
    if (newPassword) payload.new_password = newPassword;

    if (!payload.username && !payload.email && !payload.new_password) {
      setBanner({ kind: "error", text: "至少填写一项待修改字段。" });
      return;
    }

    setSaving(true);
    try {
      await updateMyProfile(payload);
      setBanner({ kind: "success", text: "账号信息已更新。" });
      setNewUsername("");
      setNewEmail("");
      setNewPassword("");
      setCurrentPassword("");
    } catch (err) {
      setBanner({
        kind: "error",
        text: (err as { message?: string })?.message || "更新失败",
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(): Promise<void> {
    setBanner(null);
    if (deleteConfirm.trim().toUpperCase() !== "DELETE") {
      setBanner({ kind: "error", text: '请在确认框中输入大写 "DELETE"。' });
      return;
    }
    if (!deletePassword) {
      setBanner({ kind: "error", text: "请输入当前密码以确认删除。" });
      return;
    }
    if (!window.confirm("确定要永久删除账号吗？此操作不可撤销。")) {
      return;
    }
    setDeleting(true);
    try {
      await deleteMyAccount({
        current_password: deletePassword,
        confirm: deleteConfirm.trim(),
      });
      router.replace("/login?reason=deleted");
    } catch (err) {
      setBanner({
        kind: "error",
        text: (err as { message?: string })?.message || "删除失败",
      });
      setDeleting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-6 py-10">
      <header>
        <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
          MY ACCOUNT
        </div>
        <h1 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          账号与数据
        </h1>
        <p className="mt-3 text-sm leading-7 text-soft">
          管理自己的账号信息，导出个人数据快照，或永久注销账号。所有操作都要求当前密码，防止 cookie 被劫持后擅自改动。
        </p>
      </header>

      {banner ? (
        <div
          className={
            banner.kind === "success"
              ? "rounded-card border border-[#c9e8dc] bg-[#f6fffb] px-4 py-3 text-sm leading-7 text-[#3d8b74]"
              : "rounded-card border border-[#f5c6cb] bg-[#fff3f5] px-4 py-3 text-sm leading-7 text-[#b44655]"
          }
        >
          {banner.text}
        </div>
      ) : null}

      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <h2 className="font-heading text-xl font-extrabold tracking-[-0.03em] text-ink">
          导出我的数据
        </h2>
        <p className="mt-2 text-sm leading-7 text-soft">
          下载 JSON 快照：账号信息、订阅、上传批次、产品档案、行动、复盘、推送设置、ASIN 监控列表。评论明细因体量原因不含在此快照中，需在「历史记录 / 下载」页单独导出。
        </p>
        <div className="mt-4">
          <Button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            className="min-h-11 rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-ink/90"
          >
            {exporting ? "导出中..." : "下载 JSON 快照"}
          </Button>
        </div>
      </section>

      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <h2 className="font-heading text-xl font-extrabold tracking-[-0.03em] text-ink">
          修改账号信息
        </h2>
        <p className="mt-2 text-sm leading-7 text-soft">
          修改用户名、邮箱或密码。任一项修改都需要输入当前密码校验身份。
        </p>
        <div className="mt-4 space-y-4">
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">当前密码 *</span>
            <Input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
              placeholder="用于校验身份"
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">新用户名</span>
            <Input
              value={newUsername}
              onChange={(event) => setNewUsername(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
              placeholder="留空表示不修改"
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">新邮箱</span>
            <Input
              type="email"
              value={newEmail}
              onChange={(event) => setNewEmail(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
              placeholder="留空表示不修改"
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">新密码</span>
            <Input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
              placeholder="至少 6 位，含字母 / 数字 / 特殊字符 / 大写"
            />
          </label>
          <div>
            <Button
              type="button"
              onClick={handleUpdate}
              disabled={saving}
              className="min-h-11 rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-ink/90"
            >
              {saving ? "保存中..." : "保存修改"}
            </Button>
          </div>
        </div>
      </section>

      <section className="rounded-shell border border-[#f5c6cb] bg-white/84 p-6 shadow-card backdrop-blur">
        <h2 className="font-heading text-xl font-extrabold tracking-[-0.03em] text-[#b44655]">
          删除账号（不可撤销）
        </h2>
        <p className="mt-2 text-sm leading-7 text-soft">
          执行后：登录凭证立即失效，用户名 / 邮箱 / 密码从数据库清除；上传批次、评论、产品档案等业务数据保留但已无法识别真人。如有活跃的 Paddle 订阅，请在删除前手动前往
          Paddle 后台取消，否则会继续扣款。
        </p>
        <div className="mt-4 space-y-4">
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">当前密码 *</span>
            <Input
              type="password"
              value={deletePassword}
              onChange={(event) => setDeletePassword(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">
              请输入 <code className="font-mono">DELETE</code> 确认
            </span>
            <Input
              value={deleteConfirm}
              onChange={(event) => setDeleteConfirm(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
              placeholder="DELETE"
            />
          </label>
          <div>
            <Button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="min-h-11 rounded-pill bg-[#b44655] px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-[#b44655]/90"
            >
              {deleting ? "删除中..." : "永久删除账号"}
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
