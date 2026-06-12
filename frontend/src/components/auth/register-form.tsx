"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { identify, track } from "@/lib/analytics";

export function RegisterForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
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

      const meRes = await fetch("/api/me", { credentials: "include" });
      if (meRes.ok) {
        const me = await meRes.json();
        identify(String(me.id), {
          username: me.username,
          email: me.email,
          plan: me.plan,
          signup_date: new Date().toISOString(),
        });
      }

      track("signup_complete", { method: "email" });
      router.push("/workspace");
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="reg-username" className="block text-sm font-medium text-ink">
          Username
        </label>
        <input
          id="reg-username"
          type="text"
          required
          minLength={2}
          maxLength={64}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="mt-1 w-full rounded-lg border border-line bg-white px-4 py-2.5 text-sm text-ink outline-none transition focus:border-[#8d7be8] focus:ring-2 focus:ring-[#8d7be8]/20"
          placeholder="your username"
        />
      </div>
      <div>
        <label htmlFor="reg-email" className="block text-sm font-medium text-ink">
          Email
        </label>
        <input
          id="reg-email"
          type="email"
          required
          maxLength={255}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full rounded-lg border border-line bg-white px-4 py-2.5 text-sm text-ink outline-none transition focus:border-[#8d7be8] focus:ring-2 focus:ring-[#8d7be8]/20"
          placeholder="you@example.com"
        />
      </div>
      <div>
        <label htmlFor="reg-password" className="block text-sm font-medium text-ink">
          Password
        </label>
        <input
          id="reg-password"
          type="password"
          required
          minLength={6}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full rounded-lg border border-line bg-white px-4 py-2.5 text-sm text-ink outline-none transition focus:border-[#8d7be8] focus:ring-2 focus:ring-[#8d7be8]/20"
          placeholder="at least 6 characters"
        />
      </div>
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 disabled:opacity-50"
      >
        {loading ? "Creating account..." : "Create Account"}
      </button>
    </form>
  );
}
