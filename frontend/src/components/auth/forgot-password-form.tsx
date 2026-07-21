"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { track } from "@/lib/analytics";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Step = "email" | "code" | "done";

export function ForgotPasswordForm() {
  const t = useTranslations("auth");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRequestCode(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/auth/password/reset/request", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // 告诉后端当前用户界面语言,mailer 会按此渲染中文/英文邮件模板。
          // 用自定义头避免 Accept-Language 被 nginx / CDN 改写。
          "X-Locale": locale,
        },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(data?.detail || `Request failed (${res.status})`);
        return;
      }

      track("password_reset_request", { step: "code_sent" });
      setStep("code");
    } catch {
      setError(tCommon("networkError"));
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmReset(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/auth/password/reset/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code, new_password: newPassword }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(data?.detail || `Reset failed (${res.status})`);
        return;
      }

      track("password_reset_confirm", { step: "success" });
      setStep("done");
    } catch {
      setError(tCommon("networkError"));
    } finally {
      setLoading(false);
    }
  }

  const inputClassName =
    "mt-1 border-line bg-white/80 text-ink focus-visible:ring-rose/20 focus-visible:border-rose rounded-xl";

  if (step === "done") {
    return (
      <div className="space-y-4 text-center">
        <p className="text-sm text-ink">{t("resetSent")}</p>
        <Button href="/login" className="rounded-pill bg-rose px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 hover:bg-rose/90">
          {t("goLogin")}
        </Button>
      </div>
    );
  }

  if (step === "code") {
    return (
      <form onSubmit={handleConfirmReset} className="space-y-4">
        <p className="text-sm text-soft">
          {t("codeSentTo")} <span className="font-medium text-ink">{email}</span>
        </p>
        <div>
          <label htmlFor="reset-code" className="block text-sm font-medium text-ink">
            {t("codeLabel")}
          </label>
          <Input
            id="reset-code"
            type="text"
            required
            minLength={4}
            maxLength={12}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className={inputClassName}
            placeholder={t("codePlaceholder")}
            autoComplete="one-time-code"
          />
        </div>
        <div>
          <label htmlFor="reset-new-password" className="block text-sm font-medium text-ink">
            {t("password")}
          </label>
          <Input
            id="reset-new-password"
            type="password"
            required
            minLength={6}
            maxLength={128}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className={inputClassName}
            placeholder={t("passwordHint")}
          />
        </div>
        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        <Button type="submit" disabled={loading} className="w-full rounded-pill bg-rose px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 hover:bg-rose/90">
          {loading ? t("confirmingReset") : t("confirmReset")}
        </Button>
        <button
          type="button"
          onClick={() => { setStep("email"); setError(""); }}
          className="w-full text-center text-sm text-soft hover:text-ink"
        >
          {t("useOtherEmail")}
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleRequestCode} className="space-y-4">
      <div>
        <label htmlFor="reset-email" className="block text-sm font-medium text-ink">
          {t("email")}
        </label>
        <Input
          id="reset-email"
          type="email"
          required
          maxLength={255}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={inputClassName}
          placeholder={t("emailPlaceholder")}
        />
      </div>
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
      <Button type="submit" disabled={loading} className="w-full rounded-pill bg-rose px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 hover:bg-rose/90">
        {loading ? t("sendingResetLink") : t("sendResetLink")}
      </Button>
    </form>
  );
}
