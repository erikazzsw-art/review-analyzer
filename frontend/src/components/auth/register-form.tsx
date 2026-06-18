"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useTranslations } from "next-intl";

import { identify, track } from "@/lib/analytics";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type AuthResponse = {
  user: {
    id: number;
    username: string;
    email?: string;
    plan?: string;
  };
};

export function RegisterForm() {
  const router = useRouter();
  const t = useTranslations("auth");
  const tCommon = useTranslations("common");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
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
    track("signup_click", { page: "/register" });

    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, email, password }),
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

      track("signup_complete", { method: "email" });
      router.push("/workspace");
    } catch {
      setError(tCommon("networkError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="reg-username" className="block text-sm font-medium text-ink">
          {t("username")}
        </label>
        <Input
          id="reg-username"
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
        <label htmlFor="reg-email" className="block text-sm font-medium text-ink">
          {t("email")}
        </label>
        <Input
          id="reg-email"
          type="email"
          required
          maxLength={255}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 border-line bg-white text-ink focus-visible:ring-lavender/20 focus-visible:border-lavender"
          placeholder={t("emailPlaceholder")}
        />
      </div>
      <div>
        <label htmlFor="reg-password" className="block text-sm font-medium text-ink">
          {t("password")}
        </label>
        <Input
          id="reg-password"
          type="password"
          required
          minLength={6}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 border-line bg-white text-ink focus-visible:ring-lavender/20 focus-visible:border-lavender"
          placeholder={t("passwordHint")}
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
        {loading ? t("registerLoading") : t("registerButton")}
      </Button>
    </form>
  );
}
