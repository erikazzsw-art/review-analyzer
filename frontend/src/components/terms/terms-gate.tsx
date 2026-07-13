"use client";

import { useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Shield } from "lucide-react";

import { acceptTerms } from "@/lib/api/browser";

const CURRENT_TERMS_VERSION = "2.0";

type TermsGateProps = {
  open: boolean;
};

export function TermsGate({ open }: TermsGateProps) {
  const t = useTranslations("auth");
  const [ageConfirmed, setAgeConfirmed] = useState(false);
  const [termsAgreed, setTermsAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  if (!open || done) return null;

  const canSubmit = ageConfirmed && termsAgreed && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError("");
    try {
      await acceptTerms(CURRENT_TERMS_VERSION);
      setDone(true);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Network error. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-lg rounded-2xl bg-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-3 rounded-t-2xl bg-lavender/10 px-6 py-5 border-b border-lavender/20">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-lavender/20">
            <Shield className="h-5 w-5 text-lavender" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-ink">
              {t("termsGateTitle")}
            </h2>
            <p className="text-sm text-soft">
              {t("termsGateSubtitle")}
            </p>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          <p className="text-sm text-ink/70 leading-relaxed">
            {t("termsGateDescription")}
          </p>

          <div className="space-y-3">
            {/* Age confirmation */}
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={ageConfirmed}
                onChange={(e) => setAgeConfirmed(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-line text-lavender accent-lavender focus:ring-lavender/20"
              />
              <span className="text-sm text-ink/80">{t("ageConfirm")}</span>
            </label>

            {/* Terms agreement */}
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={termsAgreed}
                onChange={(e) => setTermsAgreed(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-line text-lavender accent-lavender focus:ring-lavender/20"
              />
              <span className="text-sm text-ink/80">
                {t.rich("agreeTerms", {
                  terms: (chunks: React.ReactNode) => (
                    <Link
                      href="/terms"
                      target="_blank"
                      className="text-lavender underline hover:text-lavender/80"
                    >
                      {chunks}
                    </Link>
                  ),
                  privacy: (chunks: React.ReactNode) => (
                    <Link
                      href="/privacy"
                      target="_blank"
                      className="text-lavender underline hover:text-lavender/80"
                    >
                      {chunks}
                    </Link>
                  ),
                })}
              </span>
            </label>
          </div>

          {error && (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="rounded-b-2xl bg-mist/30 px-6 py-4 border-t border-line/20">
          <button
            type="button"
            disabled={!canSubmit}
            onClick={handleSubmit}
            className="w-full rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:-translate-y-0.5 hover:bg-ink/90 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0"
          >
            {submitting ? t("termsGateSubmitting") : t("termsGateSubmit")}
          </button>
        </div>
      </div>
    </div>
  );
}
