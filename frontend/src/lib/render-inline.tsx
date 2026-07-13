import type { ReactNode } from "react";
import Link from "next/link";

/**
 * Inline rich-text parser for a small tag vocabulary:
 *   <b>...</b>                        → <strong>
 *   <mail>addr@x.com</mail>           → mailto: link
 *   <link href="/path">label</link>   → internal Next <Link>
 *   <ext href="https://…">label</ext> → external <a target="_blank">
 *
 * Designed for translator-authored strings in messages JSON, not user
 * input — XSS is not a concern because content is fully controlled by us.
 * Tags without a recognised name or an href (when required) are silently
 * stripped; only their inner text survives.
 */
const TAG_RE = /<(b|mail|link|ext)(?:\s+href="([^"]+)")?>([\s\S]*?)<\/\1>/g;

export function renderInline(text: string): ReactNode {
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
        </a>,
      );
    } else if (tag === "link" && href) {
      nodes.push(
        <Link key={key++} href={href}>
          {inner}
        </Link>,
      );
    } else if (tag === "ext" && href) {
      nodes.push(
        <a key={key++} href={href} target="_blank" rel="noopener noreferrer">
          {inner}
        </a>,
      );
    }
    last = match.index + full.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes.length === 1 ? nodes[0] : <>{nodes}</>;
}
