"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { identify, track } from "@/lib/analytics";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
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
        setError(data?.detail || `Login failed (${res.status})`);
        track("login_fail", { reason: data?.detail || "unknown" });
        return;
      }

      const meRes = await fetch("/api/me", { credentials: "include" });
      if (meRes.ok) {
        const me = await meRes.json();
        identify(String(me.id), { username: me.username, plan: me.plan });
      }

      track("login_success", { method: "email" });
      router.push("/workspace");
    } catch {
      setError("Network error. Please try again.");
      track("login_fail", { reason: "network_error" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="login-username" className="block text-sm font-medium text-ink">
          Username
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
          placeholder="your username"
        />
      </div>
      <div>
        <label htmlFor="login-password" className="block text-sm font-medium text-ink">
          Password
        </label>
        <Input
          id="login-password"
          type="password"
          required
          minLength={6}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 border-line bg-white text-ink focus-visible:ring-lavender/20 focus-visible:border-lavender"
          placeholder="your password"
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
        {loading ? "Logging in..." : "Log In"}
      </Button>
    </form>
  );
}
