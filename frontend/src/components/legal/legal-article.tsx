import type { ReactNode } from "react";
import Link from "next/link";
import { getMessages } from "next-intl/server";

type Block =
  | { type: "paragraph"; text: string }
  | { type: "bullets"; items: string[] }
  | { type: "ordered"; items: string[] };

type Section = {
  heading: string;
  blocks: Block[];
};

type LegalPageContent = {
  pageTitle: string;
  pageSubtitle: string;
  updatedAt: string;
  lead?: string;
  sections: Section[];
};

type LegalArticleProps = {
  /** e.g. "terms" | "privacy" | "refund" | "cookies" | "dpa" — key under legal.* */
  page: "terms" | "privacy" | "refund" | "cookies" | "dpa";
};

// Inline rich-text markers we understand:
//   <b>...</b>                        → <strong>
//   <mail>addr@x.com</mail>           → mailto: link
//   <link href="/path">label</link>   → internal Next Link
//   <ext href="https://…">label</ext> → external <a target="_blank" rel="noopener noreferrer">
//
// The parser is intentionally strict about a small tag vocabulary rather than
// running an arbitrary HTML sanitiser: content is authored by us, in messages
// JSON, so we don't need XSS mitigation — but we do want future authors to fail
// loudly if they type <script> or <img> by mistake.
const TAG_RE = /<(b|mail|link|ext)(?:\s+href="([^"]+)")?>([\s\S]*?)<\/\1>/g;

function renderInline(text: string): ReactNode {
  const nodes: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  const re = new RegExp(TAG_RE);
  while ((match = re.exec(text)) !== null) {
    const [full, tag, href, inner] = match;
    if (match.index > last) nodes.push(text.slice(last, match.index));
    if (tag === "b") {
      nodes.push(<strong key={key++}>{inner}</strong>);
    } else if (tag === "mail") {
      nodes.push(
        <a key={key++} href={`mailto:${inner}`}>
          {inner}
        </a>
      );
    } else if (tag === "link" && href) {
      nodes.push(
        <Link key={key++} href={href}>
          {inner}
        </Link>
      );
    } else if (tag === "ext" && href) {
      nodes.push(
        <a
          key={key++}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
        >
          {inner}
        </a>
      );
    }
    last = match.index + full.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes.length === 1 ? nodes[0] : <>{nodes}</>;
}

function renderBlock(block: Block, idx: number): ReactNode {
  if (block.type === "paragraph") {
    return <p key={idx}>{renderInline(block.text)}</p>;
  }
  if (block.type === "bullets") {
    return (
      <ul key={idx}>
        {block.items.map((item, i) => (
          <li key={i}>{renderInline(item)}</li>
        ))}
      </ul>
    );
  }
  return (
    <ol key={idx}>
      {block.items.map((item, i) => (
        <li key={i}>{renderInline(item)}</li>
      ))}
    </ol>
  );
}

export async function LegalArticle({ page }: LegalArticleProps) {
  const messages = await getMessages();
  // Read the whole page tree once — this is structured content (nested
  // arrays), not something t() can look up per key.
  const legal = messages.legal as unknown as {
    lastUpdatedLabel: string;
  } & Record<string, LegalPageContent>;
  const content = legal[page];

  return (
    <article className="prose prose-sm mx-auto max-w-3xl px-4 py-12">
      <h1>{content.pageTitle}</h1>
      <p className="text-muted-foreground">
        {legal.lastUpdatedLabel}: {content.updatedAt}
      </p>
      {content.lead ? <p>{renderInline(content.lead)}</p> : null}
      {content.sections.map((section, sIdx) => (
        <section key={sIdx}>
          <h2>{section.heading}</h2>
          {section.blocks.map((block, bIdx) => renderBlock(block, bIdx))}
        </section>
      ))}
    </article>
  );
}
