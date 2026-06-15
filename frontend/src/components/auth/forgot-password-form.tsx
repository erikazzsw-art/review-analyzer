"use client";

import Link from "next/link";
import { useState } from "react";

import { track } from "@/lib/analytics";

type Step = "email" | "code" | "done";

export function ForgotPasswordForm() {
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
        headers: { "Content-Type": "application/json" },
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
      setError("Network error. Please try again.");
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
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const inputClassName =
    "mt-1 w-full rounded-lg border border-line bg-white px-4 py-2.5 text-sm text-ink outline-none transition focus:border-[#8d7be8] focus:ring-2 focus:ring-[#8d7be8]/20";
  const buttonClassName =
    "w-full rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 disabled:opacity-50";

  if (step === "done") {
    return (
      <div className="space-y-4 text-center">
        <p className="text-sm text-ink">Password reset successful.</p>
        <Link
          href="/login"
          className="inline-block rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5"
        >
          Back to Log In
        </Link>
      </div>
    );
  }

  if (step === "code") {
    return (
      <form onSubmit={handleConfirmReset} className="space-y-4">
        <p className="text-sm text-soft">
          A 6-digit code has been sent to <span className="font-medium text-ink">{email}</span>.
        </p>
        <div>
          <label htmlFor="reset-code" className="block text-sm font-medium text-ink">
            Verification Code
          </label>
          <input
            id="reset-code"
            type="text"
            required
            minLength={4}
            maxLength={12}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className={inputClassName}
            placeholder="6-digit code"
            autoComplete="one-time-code"
          />
        </div>
        <div>
          <label htmlFor="reset-new-password" className="block text-sm font-medium text-ink">
            New Password
          </label>
          <input
            id="reset-new-password"
            type="password"
            required
            minLength={6}
            maxLength={128}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className={inputClassName}
            placeholder="at least 6 characters"
          />
        </div>
        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        <button type="submit" disabled={loading} className={buttonClassName}>
          {loading ? "Resetting..." : "Reset Password"}
        </button>
        <button
          type="button"
          onClick={() => { setStep("email"); setError(""); }}
          className="w-full text-center text-sm text-soft hover:text-ink"
        >
          Use a different email
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleRequestCode} className="space-y-4">
      <div>
        <label htmlFor="reset-email" className="block text-sm font-medium text-ink">
          Email
        </label>
        <input
          id="reset-email"
          type="email"
          required
          maxLength={255}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={inputClassName}
          placeholder="you@example.com"
        />
      </div>
      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
      <button type="submit" disabled={loading} className={buttonClassName}>
        {loading ? "Sending code..." : "Send Reset Code"}
      </button>
    </form>
  );
}