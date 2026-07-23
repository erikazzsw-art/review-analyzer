"use client";

import { useState } from "react";
import { Briefcase, Check } from "lucide-react";
import { useTranslations } from "next-intl";

import { updateOccupationTag } from "@/lib/api/browser";
import type { OccupationTag, UserProfilePayload } from "@/lib/api/types";
import { identify, track } from "@/lib/analytics";
import { cn } from "@/lib/utils";

export const OCCUPATION_TAG_OPTIONS: OccupationTag[] = [
  "operations",
  "product_manager",
  "management",
  "customer_service",
  "quality_control",
  "other",
];

type OccupationTagGateProps = {
  open: boolean;
  userId: number | null;
  username: string | null;
  plan: string | null;
  onComplete: (profile: UserProfilePayload) => void;
};

export function OccupationTagGate({
  open,
  userId,
  username,
  plan,
  onComplete,
}: OccupationTagGateProps) {
  const t = useTranslations("auth");
  const [selected, setSelected] = useState<OccupationTag | null>(null);
  const [submitting, setSubmitting] = useState<"save" | "skip" | null>(null);
  const [error, setError] = useState("");

  if (!open) return null;

  const identifyOccupation = (profile: UserProfilePayload) => {
    if (!userId) return;
    identify(String(userId), {
      username: username ?? profile.username,
      plan: plan ?? profile.plan,
      occupation_tag: profile.occupation_tag ?? null,
      occupation_tag_status: profile.occupation_tag_status,
    });
  };

  const handleSave = async () => {
    if (!selected || submitting) return;
    setError("");
    setSubmitting("save");
    try {
      const profile = await updateOccupationTag({
        occupation_tag: selected,
        source: "onboarding",
      });
      identifyOccupation(profile);
      track("occupation_tag_saved", {
        occupation_tag: selected,
        source: "onboarding",
      });
      onComplete(profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("occupationGateSaveFailed"));
    } finally {
      setSubmitting(null);
    }
  };

  const handleSkip = async () => {
    if (submitting) return;
    setError("");
    setSubmitting("skip");
    try {
      const profile = await updateOccupationTag({
        skip: true,
        source: "onboarding",
      });
      identifyOccupation(profile);
      track("occupation_tag_skipped", { source: "onboarding" });
      onComplete(profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("occupationGateSaveFailed"));
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="fixed inset-0 z-[9998] flex items-center justify-center bg-black/55 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-line bg-white shadow-2xl">
        <div className="flex items-center gap-3 border-b border-line bg-[#f7fbff] px-6 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#dff0ff] text-[#4a7dc7]">
            <Briefcase className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-ink">{t("occupationGateTitle")}</h2>
            <p className="text-sm text-soft">{t("occupationGateSubtitle")}</p>
          </div>
        </div>

        <div className="space-y-5 px-6 py-5">
          <p className="text-sm leading-6 text-ink/70">{t("occupationGateDescription")}</p>

          <div className="grid gap-2 sm:grid-cols-2">
            {OCCUPATION_TAG_OPTIONS.map((option) => {
              const active = selected === option;
              return (
                <button
                  key={option}
                  type="button"
                  onClick={() => setSelected(option)}
                  className={cn(
                    "flex min-h-11 items-center justify-between rounded-md border px-3 py-2 text-left text-sm font-semibold transition",
                    active
                      ? "border-[#4a7dc7] bg-[#eef6ff] text-ink"
                      : "border-line bg-white text-ink/78 hover:border-[#4a7dc7]/60 hover:bg-[#f7fbff]"
                  )}
                >
                  <span>{t(`occupationOptions.${option}`)}</span>
                  {active ? <Check className="h-4 w-4 text-[#4a7dc7]" /> : null}
                </button>
              );
            })}
          </div>

          {error ? (
            <p className="text-sm text-red-600" role="alert">
              {error}
            </p>
          ) : null}
        </div>

        <div className="flex flex-col-reverse gap-2 border-t border-line bg-mist/30 px-6 py-4 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={handleSkip}
            disabled={submitting !== null}
            className="inline-flex min-h-10 items-center justify-center rounded-md border border-line bg-white px-4 text-sm font-semibold text-soft transition hover:bg-white/80 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting === "skip" ? t("occupationGateSkipping") : t("occupationGateSkip")}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!selected || submitting !== null}
            className="inline-flex min-h-10 items-center justify-center rounded-md bg-ink px-5 text-sm font-semibold text-white shadow-card transition hover:bg-ink/90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting === "save" ? t("occupationGateSubmitting") : t("occupationGateSubmit")}
          </button>
        </div>
      </div>
    </div>
  );
}
