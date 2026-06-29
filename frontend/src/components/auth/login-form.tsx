"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { identify, track } from "@/lib/analytics";
import { Button } from "@/components/ui/button";
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
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
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
        body: JSON.stringify({ username, password }),
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

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="login-username" className="block text-sm font-medium text-ink">
          {t("username")}
        </label>
        <Input
          id="login-username"
          type="text"
          required
          minLength={2}
          maxLength={64}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="mt-1 border-line bg-white text-ink focus-visible:ring-lavender/20 focus-visible:border-lavender"
          placeholder={t("usernamePlaceholder")}
        />
      </div>
      <div>
        <label htmlFor="login-password" className="block text-sm font-medium text-ink">
          {t("password")}
        </label>
        <PasswordInput
          id="login-password"
          required
          minLength={6}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 border-line bg-white text-ink focus-visible:ring-lavender/20 focus-visible:border-lavender"
          placeholder={t("passwordPlaceholder")}
        />
      </div>
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
      <Button
        type="submit"
        disabled={loading}
        className="w-full rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 hover:bg-ink/90"
      >
        {loading ? t("loginLoading") : t("loginButton")}
      </Button>
    </form>
  );
}
