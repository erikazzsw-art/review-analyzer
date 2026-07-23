"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
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

export function TrialForm() {
  const router = useRouter();
  const t = useTranslations("trial");
  const tCommon = useTranslations("common");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canSubmit = email.trim().length > 0 && password.length >= 6;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading || !canSubmit) return;

    setError("");
    setLoading(true);
    track("trial_signup_click", { page: "/trial" });

    try {
      const username = email.split("@")[0] || email;

      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          username,
          email,
          password,
          terms_version: "2.0",
          age_confirmed: true,
          marketing_opt_in: false,
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

      track("trial_signup_complete", { method: "email" });

      router.push("/workspace");
    } catch {
      setError(tCommon("networkError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Title */}
      <div className="text-center">
        <h2 className="font-heading text-xl font-extrabold tracking-normal text-[#25212a]">
          {t("formTitle")}
        </h2>
        <p className="mt-1.5 text-sm text-[#6f6877]">{t("formSubtitle")}</p>
      </div>

      {/* Email */}
      <div>
        <Input
          type="email"
          required
          maxLength={255}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("emailPlaceholder")}
          className="border-[rgba(255,255,255,0.8)] bg-white/60 text-[#25212a] placeholder:text-[#b8b0c0] focus-visible:border-[#f36f8f] focus-visible:ring-[#f36f8f]/15"
          style={{ height: "44px", borderRadius: "12px" }}
        />
      </div>

      {/* Password */}
      <div>
        <PasswordInput
          required
          minLength={6}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t("passwordPlaceholder")}
          className="border-[rgba(255,255,255,0.8)] bg-white/60 text-[#25212a] placeholder:text-[#b8b0c0] focus-visible:border-[#f36f8f] focus-visible:ring-[#f36f8f]/15"
          style={{ height: "44px", borderRadius: "12px" }}
        />
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={loading || !canSubmit}
        className="flex w-full items-center justify-center rounded-[12px] bg-[#f36f8f] px-5 text-sm font-semibold text-white shadow-[0_8px_24px_rgba(243,111,143,0.35)] transition hover:-translate-y-0.5 hover:bg-[#f36f8f]/90 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
        style={{ height: "44px" }}
      >
        {loading ? t("starting") : t("startTrial")}
      </button>

      {/* Login link */}
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
            <Link href="/terms" className="text-[#f36f8f] hover:underline">
              {chunks}
            </Link>
          ),
          privacy: (chunks: React.ReactNode) => (
            <Link href="/privacy" className="text-[#f36f8f] hover:underline">
              {chunks}
            </Link>
          ),
        })}
      </p>
    </form>
  );
}
