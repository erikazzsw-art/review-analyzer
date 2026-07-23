"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import {
  deleteMyAccount,
  exportMyData,
  updateOccupationTag,
  updateMyProfile,
} from "@/lib/api/browser";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OCCUPATION_TAG_OPTIONS } from "@/components/onboarding/occupation-tag-gate";
import { identify, track } from "@/lib/analytics";
import { cn } from "@/lib/utils";
import type { OccupationTag, UserProfilePayload } from "@/lib/api/types";

type Banner = { kind: "success" | "error"; text: string } | null;

export default function AccountSettingsPage() {
  const t = useTranslations("settings.account");
  const tAuth = useTranslations("auth");
  const router = useRouter();

  const [profile, setProfile] = useState<UserProfilePayload | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [occupationTag, setOccupationTag] = useState<OccupationTag | "">("");
  const [occupationSaving, setOccupationSaving] = useState(false);

  const [exporting, setExporting] = useState(false);

  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const [deleting, setDeleting] = useState(false);

  const [banner, setBanner] = useState<Banner>(null);

  useEffect(() => {
    fetch("/api/me", { credentials: "include" })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (!payload) return;
        const nextProfile = payload as UserProfilePayload;
        setProfile(nextProfile);
        setOccupationTag(nextProfile.occupation_tag ?? "");
      })
      .catch(() => {});
  }, []);

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
      setBanner({ kind: "success", text: t("exportSuccess") });
    } catch (err) {
      setBanner({
        kind: "error",
        text: (err as { message?: string })?.message || t("exportFail"),
      });
    } finally {
      setExporting(false);
    }
  }

  async function handleUpdate(): Promise<void> {
    setBanner(null);
    if (!currentPassword) {
      setBanner({ kind: "error", text: t("updateNeedCurrent") });
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
      setBanner({ kind: "error", text: t("updateNeedField") });
      return;
    }

    setSaving(true);
    try {
      await updateMyProfile(payload);
      setBanner({ kind: "success", text: t("updateSuccess") });
      setNewUsername("");
      setNewEmail("");
      setNewPassword("");
      setCurrentPassword("");
    } catch (err) {
      setBanner({
        kind: "error",
        text: (err as { message?: string })?.message || t("updateFail"),
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleOccupationSave(): Promise<void> {
    setBanner(null);
    if (!occupationTag) {
      setBanner({ kind: "error", text: t("occupationNeedSelection") });
      return;
    }

    setOccupationSaving(true);
    try {
      const nextProfile = await updateOccupationTag({
        occupation_tag: occupationTag,
        source: "account_settings",
      });
      setProfile(nextProfile);
      setOccupationTag(nextProfile.occupation_tag ?? "");
      identify(String(nextProfile.id), {
        username: nextProfile.username,
        plan: nextProfile.plan,
        occupation_tag: nextProfile.occupation_tag,
        occupation_tag_status: nextProfile.occupation_tag_status,
      });
      track("occupation_tag_saved", {
        occupation_tag: nextProfile.occupation_tag,
        source: "account_settings",
      });
      setBanner({ kind: "success", text: t("occupationSaveSuccess") });
    } catch (err) {
      setBanner({
        kind: "error",
        text: (err as { message?: string })?.message || t("occupationSaveFail"),
      });
    } finally {
      setOccupationSaving(false);
    }
  }

  async function handleDelete(): Promise<void> {
    setBanner(null);
    if (deleteConfirm.trim().toUpperCase() !== "DELETE") {
      setBanner({ kind: "error", text: t("deleteNeedText") });
      return;
    }
    if (!deletePassword) {
      setBanner({ kind: "error", text: t("deleteNeedPassword") });
      return;
    }
    if (!window.confirm(t("deleteConfirmPrompt"))) {
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
        text: (err as { message?: string })?.message || t("deleteFail"),
      });
      setDeleting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-6 py-10">
      <header>
        <div className="inline-flex rounded-pill bg-[#eef6ff] px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#4a7dc7]">
          {t("badge")}
        </div>
        <h1 className="mt-4 font-heading text-3xl font-extrabold tracking-[-0.04em] text-ink">
          {t("title")}
        </h1>
        <p className="mt-3 text-sm leading-7 text-soft">
          {t("description")}
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
          {t("exportTitle")}
        </h2>
        <p className="mt-2 text-sm leading-7 text-soft">
          {t("exportDesc")}
        </p>
        <div className="mt-4">
          <Button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            className="min-h-11 rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-ink/90"
          >
            {exporting ? t("exportBtnLoading") : t("exportBtn")}
          </Button>
        </div>
      </section>

      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <h2 className="font-heading text-xl font-extrabold tracking-[-0.03em] text-ink">
          {t("occupationTitle")}
        </h2>
        <p className="mt-2 text-sm leading-7 text-soft">
          {t("occupationDesc")}
        </p>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {OCCUPATION_TAG_OPTIONS.map((option) => {
            const active = occupationTag === option;
            return (
              <button
                key={option}
                type="button"
                onClick={() => setOccupationTag(option)}
                className={cn(
                  "min-h-11 rounded-md border px-3 py-2 text-left text-sm font-semibold transition",
                  active
                    ? "border-[#4a7dc7] bg-[#eef6ff] text-ink"
                    : "border-line bg-white text-ink/78 hover:border-[#4a7dc7]/60 hover:bg-[#f7fbff]"
                )}
              >
                {tAuth(`occupationOptions.${option}`)}
              </button>
            );
          })}
        </div>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs leading-5 text-soft">
            {profile?.occupation_tag_status === "skipped"
              ? t("occupationSkippedHint")
              : t("occupationCurrentHint")}
          </p>
          <Button
            type="button"
            onClick={handleOccupationSave}
            disabled={occupationSaving || !occupationTag}
            className="min-h-11 rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-ink/90"
          >
            {occupationSaving ? t("occupationSaveLoading") : t("occupationSaveBtn")}
          </Button>
        </div>
      </section>

      <section className="rounded-shell border border-line bg-white/84 p-6 shadow-card backdrop-blur">
        <h2 className="font-heading text-xl font-extrabold tracking-[-0.03em] text-ink">
          {t("updateTitle")}
        </h2>
        <p className="mt-2 text-sm leading-7 text-soft">
          {t("updateDesc")}
        </p>
        <div className="mt-4 space-y-4">
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">{t("currentPasswordLabel")}</span>
            <Input
              type="password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
              placeholder={t("currentPasswordPlaceholder")}
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">{t("newUsernameLabel")}</span>
            <Input
              value={newUsername}
              onChange={(event) => setNewUsername(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
              placeholder={t("newUsernamePlaceholder")}
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">{t("newEmailLabel")}</span>
            <Input
              type="email"
              value={newEmail}
              onChange={(event) => setNewEmail(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
              placeholder={t("newEmailPlaceholder")}
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">{t("newPasswordLabel")}</span>
            <Input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
              placeholder={t("newPasswordPlaceholder")}
            />
          </label>
          <div>
            <Button
              type="button"
              onClick={handleUpdate}
              disabled={saving}
              className="min-h-11 rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-ink/90"
            >
              {saving ? t("updateBtnLoading") : t("updateBtn")}
            </Button>
          </div>
        </div>
      </section>

      <section className="rounded-shell border border-[#f5c6cb] bg-white/84 p-6 shadow-card backdrop-blur">
        <h2 className="font-heading text-xl font-extrabold tracking-[-0.03em] text-[#b44655]">
          {t("deleteTitle")}
        </h2>
        <p className="mt-2 text-sm leading-7 text-soft">
          {t("deleteDesc")}
        </p>
        <div className="mt-4 space-y-4">
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">{t("currentPasswordLabel")}</span>
            <Input
              type="password"
              value={deletePassword}
              onChange={(event) => setDeletePassword(event.target.value)}
              className="rounded-card border-line bg-white text-sm"
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-ink">
              {t("deleteConfirmLabel")} <code className="font-mono">DELETE</code> {t("deleteConfirmSuffix")}
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
              {deleting ? t("deleteBtnLoading") : t("deleteBtn")}
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
