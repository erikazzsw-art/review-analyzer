"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { identify, track } from "@/lib/analytics";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";

type AuthResponse = {
  user: {
    id: number;
    username: string;
    email?: string;
    plan?: string;
  };
};

export function LoginForm() {
  const t = useTranslations("auth");
  const tCommon = useTranslations("common");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) {
      return;
    }
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username: email, password, remember_me: rememberMe }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(data?.detail || `${t("loginFailed")} (${res.status})`);
        track("login_fail", { reason: data?.detail || "unknown" });
        setLoading(false);
        return;
      }

      const payload = (await res.json()) as AuthResponse;
      identify(String(payload.user.id), {
        username: payload.user.username,
        plan: payload.user.plan ?? "free",
      });

      track("login_success", { method: "email" });
      window.location.href = "/workspace";
    } catch {
      setError(tCommon("networkError"));
      track("login_fail", { reason: "network_error" });
      setLoading(false);
    }
  }

  /** Redirect to Google OAuth */
  function handleGoogleLogin() {
    track("login_click", { page: "/login", method: "google" });
    window.location.href = "/api/auth/google";
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Google SSO button */}
      <button
        type="button"
        onClick={handleGoogleLogin}
        className="flex w-full items-center justify-center gap-3 rounded-[12px] border border-[rgba(0,0,0,0.08)] bg-white px-4 py-[11px] text-sm font-medium text-[#25212a] transition hover:bg-white/90 hover:shadow-sm"
        style={{ height: "44px" }}
      >
        {/* Google "G" icon */}
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
        {t("googleLogin")}
      </button>

      {/* Divider "或" */}
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-[rgba(0,0,0,0.08)]" />
        <span className="text-xs text-[#6f6877]">{t("orDivider")}</span>
        <div className="h-px flex-1 bg-[rgba(0,0,0,0.08)]" />
      </div>

      {/* Email / Username — API 同时支持邮箱和用户名登录，前端不做 email 格式校验 */}
      <div>
        <label htmlFor="login-email" className="block text-sm font-medium text-[#25212a]">
          {t("email")}
        </label>
        <Input
          id="login-email"
          type="text"
          required
          maxLength={255}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("loginEmailPlaceholder")}
          className="mt-1.5 border-[rgba(0,0,0,0.08)] bg-white text-[#25212a] placeholder:text-[#b8b0c0] focus-visible:border-[#f36f8f] focus-visible:ring-[#f36f8f]/15"
          style={{ height: "44px", borderRadius: "12px" }}
        />
      </div>

      {/* Password */}
      <div>
        <label htmlFor="login-password" className="block text-sm font-medium text-[#25212a]">
          {t("password")}
        </label>
        <PasswordInput
          id="login-password"
          required
          minLength={6}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t("passwordPlaceholder")}
          className="mt-1.5 border-[rgba(0,0,0,0.08)] bg-white text-[#25212a] placeholder:text-[#b8b0c0] focus-visible:border-[#f36f8f] focus-visible:ring-[#f36f8f]/15"
          style={{ height: "44px", borderRadius: "12px" }}
        />
      </div>

      {/* Remember me + Forgot password — same row */}
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
            className="h-4 w-4 rounded border-[rgba(0,0,0,0.15)] text-[#f36f8f] accent-[#f36f8f] focus:ring-[#f36f8f]/20"
          />
          <span className="text-sm text-[#6f6877]">{t("rememberMe")}</span>
        </label>
        <Link href="/forgot-password" className="text-sm text-[#6f6877] hover:text-[#25212a] hover:underline">
          {t("forgotPassword")}
        </Link>
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {/* Submit button — rose, full-width, shadow */}
      <button
        type="submit"
        disabled={loading}
        className="flex w-full items-center justify-center rounded-[12px] bg-[#f36f8f] px-5 text-sm font-semibold text-white shadow-[0_8px_24px_rgba(243,111,143,0.35)] transition hover:-translate-y-0.5 hover:bg-[#f36f8f]/90 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
        style={{ height: "44px" }}
      >
        {loading ? t("loginLoading") : t("loginButton")}
      </button>

      {/* "还没有账号？去注册" */}
      <p className="text-center text-sm text-[#6f6877]">
        {t("noAccount")}
        <Link href="/register" className="ml-1 font-semibold text-[#f36f8f] hover:underline">
          {t("goRegister")}
        </Link>
      </p>
    </form>
  );
}
