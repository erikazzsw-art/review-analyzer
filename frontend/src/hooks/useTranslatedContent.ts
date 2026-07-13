"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useLocale } from "next-intl";
import { translateModule } from "@/lib/api/browser";

interface UseTranslatedContentOptions {
  /** Module key matching backend module_key (e.g. "consumer_profile", "user_experience") */
  moduleKey: string;
  /** Session ID for cache scoping; 0 for aggregated views without a session */
  sessionId: number;
  /** English content object to translate */
  content: Record<string, unknown>;
}

interface UseTranslatedContentResult {
  /** Translated data when available and locale is zh; null otherwise */
  translatedData: Record<string, unknown> | null;
  /** True while the translation API call is in flight */
  isLoading: boolean;
  /** True if translation failed and we're silently falling back to English */
  isFallback: boolean;
  /** True when the current locale requires translation (i.e. locale === "zh") */
  needsTranslation: boolean;
  /** Whether translated content is currently shown (togglable by user) */
  showTranslation: boolean;
  /** Toggle between showing translated content and the original English */
  toggleTranslation: () => void;
}

/**
 * Auto-translates analysis module content when the user's locale is zh.
 *
 * Behaviour:
 * - locale !== "zh" → returns content as-is (no API call)
 * - locale === "zh" → fetches translation from `POST /api/translate/module`
 *   - Backend caches by content hash — same content never costs credits twice
 *   - Loading state → shows original (English) until translation arrives
 *   - Error state → silently falls back to English (no white screen)
 * - User can toggle between translation and original via `toggleTranslation()`
 */
export function useTranslatedContent({
  moduleKey,
  sessionId,
  content,
}: UseTranslatedContentOptions): UseTranslatedContentResult {
  const locale = useLocale();
  const needsTranslation = locale === "zh";

  const [translatedData, setTranslatedData] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isFallback, setIsFallback] = useState(false);
  const [showTranslation, setShowTranslation] = useState(true);

  // Track the last-fetched content key to avoid duplicate calls on re-render
  const lastContentKey = useRef<string>("");

  const contentKey =
    needsTranslation && content && Object.keys(content).length > 0
      ? JSON.stringify(content)
      : "";

  useEffect(() => {
    if (!needsTranslation || !contentKey) {
      setTranslatedData(null);
      setIsLoading(false);
      setIsFallback(false);
      return;
    }

    // Bail if content hasn't changed since last fetch
    if (contentKey === lastContentKey.current) return;

    lastContentKey.current = contentKey;
    let cancelled = false;

    setIsLoading(true);
    setIsFallback(false);
    setShowTranslation(true);

    translateModule({
      sessionId,
      moduleKey,
      content,
      targetLang: "zh",
    })
      .then((result) => {
        if (!cancelled) {
          setTranslatedData(result.translated);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setIsFallback(true);
          setTranslatedData(null);
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [contentKey, needsTranslation, sessionId, moduleKey, content]);

  const toggleTranslation = useCallback(() => {
    setShowTranslation((prev) => !prev);
  }, []);

  if (!needsTranslation) {
    return {
      translatedData: null,
      isLoading: false,
      isFallback: false,
      needsTranslation: false,
      showTranslation: false,
      toggleTranslation,
    };
  }

  const effectiveData =
    showTranslation && translatedData ? translatedData : null;

  return {
    translatedData: effectiveData,
    isLoading,
    isFallback,
    needsTranslation: true,
    showTranslation,
    toggleTranslation,
  };
}
