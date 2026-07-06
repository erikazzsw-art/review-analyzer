import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Cookie Policy | ClueAI",
  description: "How ClueAI uses cookies and similar technologies.",
  path: "/cookies",
});

// TODO(M2.4): Replace this placeholder with the full Cookie Policy content.
// Tracked under 出海 M2.4 (cookies/dpa page bodies).
export default function CookiesPage() {
  return (
    <MarketingShell
      title="Cookie Policy"
      description="How ClueAI uses cookies and similar technologies."
    >
      <article className="prose prose-sm mx-auto max-w-3xl px-4 py-12">
        <p className="text-muted-foreground">
          Full Cookie Policy is being drafted alongside the EU Cookie Banner.
          Until it is published, ClueAI uses only strictly necessary
          session cookies to keep you signed in — no third-party tracking
          cookies, no advertising cookies.
        </p>
        <p className="text-muted-foreground">
          Questions? Email{" "}
          <a href="mailto:privacy@clueai-reviewlens.com">
            privacy@clueai-reviewlens.com
          </a>
          .
        </p>
      </article>
    </MarketingShell>
  );
}
