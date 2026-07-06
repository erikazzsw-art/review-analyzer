import { MarketingShell } from "@/components/marketing/marketing-shell";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Data Processing Agreement | ClueAI",
  description: "ClueAI Data Processing Agreement for business customers.",
  path: "/dpa",
});

// TODO(M2.4): Replace this placeholder with the full DPA text (GDPR Art. 28 SCCs).
// Tracked under 出海 M2.4 (cookies/dpa page bodies).
export default function DpaPage() {
  return (
    <MarketingShell
      title="Data Processing Agreement"
      description="ClueAI Data Processing Agreement for business customers."
    >
      <article className="prose prose-sm mx-auto max-w-3xl px-4 py-12">
        <p className="text-muted-foreground">
          Our full Data Processing Agreement (including EU Standard Contractual
          Clauses) is being finalized. Business customers who need a signed DPA
          before it is published can request one by emailing{" "}
          <a href="mailto:privacy@clueai-reviewlens.com">
            privacy@clueai-reviewlens.com
          </a>{" "}
          — we will countersign within two business days.
        </p>
        <p className="text-muted-foreground">
          Our current sub-processor list is available at{" "}
          <a href="/sub-processors">/sub-processors</a>.
        </p>
      </article>
    </MarketingShell>
  );
}
