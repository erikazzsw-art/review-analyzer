import { LegalLayout, type TocItem } from "@/components/legal/legal-layout";
import { buildMarketingMetadata } from "@/lib/seo";

export const metadata = buildMarketingMetadata({
  title: "Privacy Policy — ClueAI ReviewLens Extension",
  description:
    "Privacy policy for the ClueAI ReviewLens Chrome extension.",
  path: "/privacy-extension",
});

const TOC_ITEMS: TocItem[] = [
  { id: "what-we-access", label: "What We Access" },
  { id: "what-we-do-not-do", label: "What We Do Not Do" },
  { id: "data-storage", label: "Data Storage" },
  { id: "uploads-to-clueai", label: "Uploads to ClueAI" },
  { id: "permissions", label: "Permissions" },
  { id: "contact", label: "Contact" },
];

export default function PrivacyExtensionPage() {
  return (
    <LegalLayout tocItems={TOC_ITEMS}>
      <article className="prose prose-sm max-w-none">
        <h1>ClueAI ReviewLens Extension — Privacy Policy</h1>
        <p className="text-muted-foreground">Last updated: 2026-07-15</p>

        <section id="what-we-access">
          <h2>What We Access</h2>
          <p>
            The extension reads the publicly visible review content (review text,
            rating, date, reviewer display name, verified-purchase badge, helpful
            count) on the Amazon product or reviews page you are actively viewing,
            and only when you click the &ldquo;Scrape&rdquo; button.
          </p>
        </section>

        <section id="what-we-do-not-do">
          <h2>What We Do Not Do</h2>
          <ul>
            <li>We do not track your browsing history.</li>
            <li>
              We do not read content from tabs other than the Amazon page you
              scrape.
            </li>
            <li>
              We do not collect your name, email, payment info, or any personal
              data through the extension itself.
            </li>
          </ul>
        </section>

        <section id="data-storage">
          <h2>Data Storage</h2>
          <p>
            Scraped reviews are stored locally in your browser (
            <code>chrome.storage</code>) until you export them or upload them.
            Clearing the data removes them from local storage.
          </p>
        </section>

        <section id="uploads-to-clueai">
          <h2>Uploads to ClueAI</h2>
          <p>
            If you choose &ldquo;Upload to ClueAI,&rdquo; the scraped review data
            is sent to <code>api.clueai-reviewlens.com</code> over HTTPS,
            associated with your signed-in ClueAI account. This requires you to
            be logged in. See the{" "}
            <a href="/privacy">ClueAI main Privacy Policy</a> for how uploaded
            data is handled.
          </p>
        </section>

        <section id="permissions">
          <h2>Permissions</h2>
          <p>
            See the permission justifications in the Chrome Web Store listing for
            details on each permission the extension requests.
          </p>
        </section>

        <section id="contact">
          <h2>Contact</h2>
          <p>
            Questions? Contact us at{" "}
            <a href="mailto:support@clueai-reviewlens.com">
              support@clueai-reviewlens.com
            </a>
          </p>
        </section>
      </article>
    </LegalLayout>
  );
}
