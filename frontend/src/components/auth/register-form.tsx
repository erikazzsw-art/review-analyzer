"use client";

import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { useTranslations } from "next-intl";

import { identify, track } from "@/lib/analytics";
import { openBillingCheckout, isUnauthenticatedCheckoutError } from "@/lib/billing";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { cn } from "@/lib/utils";

type AuthResponse = {
  user: {
    id: number;
    username: string;
    email?: string;
    plan?: string;
  };
};

function checkPasswordStrength(password: string) {
  return {
    hasMinLength: password.length >= 6,
    hasLetter: /[a-zA-Z]/.test(password),
    hasNumber: /[0-9]/.test(password),
    hasSymbol: /[^a-zA-Z0-9]/.test(password),
    hasUppercase: /[A-Z]/.test(password),
  };
}

const PAID_PLAN_KEYS = new Set(["starter", "pro"]);

export function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const t = useTranslations("auth");
  const tCommon = useTranslations("common");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);
  // V4-出海-M2.5: 注册合规勾选
  const [ageConfirmed, setAgeConfirmed] = useState(false);
  const [termsAgreed, setTermsAgreed] = useState(false);
  const [marketingOptIn, setMarketingOptIn] = useState(false);

  const strength = checkPasswordStrength(password);
  const allRulesPassed = Object.values(strength).every(Boolean);
  const passwordsMatch = confirmPassword === "" || password === confirmPassword;
  const canSubmit = allRulesPassed && passwordsMatch && ageConfirmed && termsAgreed;

  const rawPlan = searchParams.get("plan");
  const rawPeriod = searchParams.get("period");
  const intendedPlan = rawPlan && PAID_PLAN_KEYS.has(rawPlan) ? rawPlan : null;
  const intendedPeriod = (rawPeriod === "monthly" || rawPeriod === "annual") ? rawPeriod : "monthly";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;

    if (!canSubmit) {
      if (!allRulesPassed) setError(t("passwordTooWeak"));
      else if (!passwordsMatch) setError(t("passwordMismatch"));
      return;
    }

    setError("");
    setLoading(true);
    track("signup_click", { page: "/register", intended_plan: intendedPlan });

    try {
      // Derive username from email (local part) since v3 form has no username field
      const username = email.split("@")[0] || email;

      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          username,
          email,
          password,
          terms_version: "1.0",
          age_confirmed: true,
          marketing_opt_in: marketingOptIn,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        setError(data?.detail || `Registration failed (${res.status})`);
        return;
      }

      const payload = (await res.json()) as AuthResponse;
      identify(String(payload.user.id), {
        username: payload.user.username,
        email: payload.user.email,
        plan: payload.user.plan ?? "free",
        signup_date: new Date().toISOString(),
      });

      track("signup_complete", { method: "email", intended_plan: intendedPlan });

      if (intendedPlan) {
        track("signup_checkout_intent", { plan: intendedPlan });
        try {
          await openBillingCheckout(null, intendedPlan as "starter" | "pro", intendedPeriod as "monthly" | "annual");
        } catch (err) {
          if (isUnauthenticatedCheckoutError(err)) {
            router.push("/workspace");
            return;
          }
        }
        router.push("/workspace");
        return;
      }

      router.push("/workspace");
    } catch {
      setError(tCommon("networkError"));
    } finally {
      setLoading(false);
    }
  }

  /** Redirect to Google OAuth */
  function handleGoogleSignUp() {
    track("signup_click", { page: "/register", method: "google" });
    window.location.href = "/api/auth/google";
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Google SSO button */}
      <button
        type="button"
        onClick={handleGoogleSignUp}
        className="flex w-full items-center justify-center gap-3 rounded-[12px] border border-[rgba(255,255,255,0.8)] bg-white/60 px-4 py-[11px] text-sm font-medium text-[#25212a] backdrop-blur transition hover:bg-white/90 hover:shadow-sm"
        style={{ height: "44px" }}
      >
        {/* Google "G" icon */}
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
        {t("googleSignUp")}
      </button>

      {/* Divider "或" */}
      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-[rgba(0,0,0,0.1)]" />
        <span className="text-xs text-[#6f6877]">{t("orDivider")}</span>
        <div className="h-px flex-1 bg-[rgba(0,0,0,0.1)]" />
      </div>

      {/* Email */}
      <div>
        <label htmlFor="reg-email" className="block text-sm font-medium text-[#25212a]">
          {t("email")}
        </label>
        <Input
          id="reg-email"
          type="email"
          required
          maxLength={255}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("emailPlaceholder")}
          className="mt-1.5 border-[rgba(255,255,255,0.8)] bg-white/60 text-[#25212a] placeholder:text-[#b8b0c0] focus-visible:border-[#f36f8f] focus-visible:ring-[#f36f8f]/15"
          style={{ height: "44px", borderRadius: "12px" }}
        />
      </div>

      {/* Password */}
      <div>
        <label htmlFor="reg-password" className="block text-sm font-medium text-[#25212a]">
          {t("password")}
        </label>
        <PasswordInput
          id="reg-password"
          required
          minLength={6}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onFocus={() => setPasswordFocused(true)}
          onBlur={() => setPasswordFocused(false)}
          placeholder={t("passwordHint")}
          className="mt-1.5 border-[rgba(255,255,255,0.8)] bg-white/60 text-[#25212a] placeholder:text-[#b8b0c0] focus-visible:border-[#f36f8f] focus-visible:ring-[#f36f8f]/15"
          style={{ height: "44px", borderRadius: "12px" }}
        />
        {/* Password strength rules */}
        {(passwordFocused || password.length > 0) && (
          <ul className="mt-2 space-y-1 text-xs">
            {([
              ["hasMinLength", t("ruleMinLength")] as const,
              ["hasLetter", t("ruleLetter")] as const,
              ["hasNumber", t("ruleNumber")] as const,
              ["hasSymbol", t("ruleSymbol")] as const,
              ["hasUppercase", t("ruleUppercase")] as const,
            ]).map(([key, label]) => (
              <li
                key={key}
                className={cn(
                  "flex items-center gap-1.5",
                  strength[key] ? "text-emerald-600" : "text-ink/40"
                )}
              >
                <span
                  className={cn(
                    "inline-block h-1.5 w-1.5 rounded-full",
                    strength[key] ? "bg-emerald-500" : "bg-ink/20"
                  )}
                />
                {label}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Confirm Password */}
      <div>
        <label htmlFor="reg-confirm-password" className="block text-sm font-medium text-[#25212a]">
          {t("confirmPassword")}
        </label>
        <PasswordInput
          id="reg-confirm-password"
          required
          minLength={6}
          maxLength={128}
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="••••••••"
          className="mt-1.5 border-[rgba(255,255,255,0.8)] bg-white/60 text-[#25212a] placeholder:text-[#b8b0c0] focus-visible:border-[#f36f8f] focus-visible:ring-[#f36f8f]/15"
          style={{ height: "44px", borderRadius: "12px" }}
        />
        {confirmPassword && !passwordsMatch && (
          <p className="mt-1 text-xs text-red-500">{t("passwordMismatch")}</p>
        )}
      </div>

      {/* Compliance checkboxes */}
      <div className="space-y-2">
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={ageConfirmed}
            onChange={(e) => setAgeConfirmed(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-[rgba(0,0,0,0.15)] text-[#f36f8f] accent-[#f36f8f] focus:ring-[#f36f8f]/20"
          />
          <span className="text-sm text-ink/80">{t("ageConfirm")}</span>
        </label>
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={termsAgreed}
            onChange={(e) => setTermsAgreed(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-[rgba(0,0,0,0.15)] text-[#f36f8f] accent-[#f36f8f] focus:ring-[#f36f8f]/20"
          />
          <span className="text-sm text-ink/80">
            {t.rich("agreeTerms", {
              terms: (chunks: React.ReactNode) => (
                <Link href="/terms" className="text-[#f36f8f] underline hover:text-[#f36f8f]/80">{chunks}</Link>
              ),
              privacy: (chunks: React.ReactNode) => (
                <Link href="/privacy" className="text-[#f36f8f] underline hover:text-[#f36f8f]/80">{chunks}</Link>
              ),
            })}
          </span>
        </label>
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={marketingOptIn}
            onChange={(e) => setMarketingOptIn(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-[rgba(0,0,0,0.15)] text-[#f36f8f] accent-[#f36f8f] focus:ring-[#f36f8f]/20"
          />
          <span className="text-sm text-ink/80">{t("marketingOptIn")}</span>
        </label>
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {/* Submit button — rose, full-width, shadow */}
      <button
        type="submit"
        disabled={loading || !canSubmit}
        className="flex w-full items-center justify-center rounded-[12px] bg-[#f36f8f] px-5 text-sm font-semibold text-white shadow-[0_8px_24px_rgba(243,111,143,0.35)] transition hover:-translate-y-0.5 hover:bg-[#f36f8f]/90 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
        style={{ height: "44px" }}
      >
        {loading ? t("registerLoading") : t("registerButton")}
      </button>

      {/* "已有账户？登录" */}
      <p className="text-center text-sm text-[#6f6877]">
        {t("hasAccount")}
        <Link href="/login" className="ml-1 font-semibold text-[#f36f8f] hover:underline">
          {t("goLogin")}
        </Link>
      </p>

      {/* Terms footnote */}
      <p className="text-center text-xs text-[#6f6877]">
        {t.rich("agreeTermsShort", {
          terms: (chunks: React.ReactNode) => (
            <Link href="/terms" className="text-[#f36f8f] hover:underline">{chunks}</Link>
          ),
          privacy: (chunks: React.ReactNode) => (
            <Link href="/privacy" className="text-[#f36f8f] hover:underline">{chunks}</Link>
          ),
        })}
      </p>
    </form>
  );
}
