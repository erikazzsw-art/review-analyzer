import { aspectLabel } from "@/lib/aspect-labels";

type RecordValue = Record<string, unknown>;

const BROAD_LABELS = new Set([
  "accessories and storage",
  "accessory storage",
  "aesthetics",
  "assembly",
  "build quality",
  "capacity",
  "comfort",
  "durability",
  "ease of use",
  "grip",
  "material",
  "materials",
  "mobility",
  "organization",
  "other",
  "packaging",
  "quality",
  "product quality",
  "stability",
  "user experience",
  "waterproof performance",
  "waterproofing",
]);

const BROAD_LABELS_ZH = new Set([
  "其他",
  "做工",
  "包装",
  "外观设计",
  "容量/空间",
  "材质用料",
  "产品质量",
  "用户体验",
  "组装难度",
  "耐用性",
  "舒适度",
  "防水性",
  "稳固性",
  "易用性",
  "抓地力",
  "活动灵活性",
  "收纳分区",
]);

function normText(value: string): string {
  return value
    .replace(/&/g, " and ")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function hasCjk(value: string): boolean {
  return /[\u3400-\u9fff]/.test(value);
}

export function splitTagText(value: unknown): string[] {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}

export function parseAspectsPayload(comment: RecordValue): RecordValue | null {
  const raw = comment.aspects_json;
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    return raw as RecordValue;
  }
  if (typeof raw === "string" && raw.trim()) {
    try {
      const parsed = JSON.parse(raw) as unknown;
      return parsed && typeof parsed === "object" && !Array.isArray(parsed)
        ? (parsed as RecordValue)
        : null;
    } catch {
      return null;
    }
  }
  return null;
}

export function getAspects(comment: RecordValue): RecordValue[] {
  const aspects = parseAspectsPayload(comment)?.aspects;
  return Array.isArray(aspects)
    ? aspects.filter((item): item is RecordValue => Boolean(item) && typeof item === "object")
    : [];
}

export function isCustomerLabelAllowed(
  label: string,
  locale: string,
  aspectKey = "",
  aspectDisplayLabel = "",
): boolean {
  const cleaned = label.trim();
  if (!cleaned) return false;
  if (locale.startsWith("en") && hasCjk(cleaned)) return false;
  if (BROAD_LABELS_ZH.has(cleaned)) return false;
  const normalized = normText(cleaned);
  if (!normalized && !BROAD_LABELS_ZH.has(cleaned)) return true;
  if (BROAD_LABELS.has(normalized)) return false;
  if (aspectKey && normalized === normText(aspectKey)) return false;
  if (aspectDisplayLabel && (normalized === normText(aspectDisplayLabel) || cleaned === aspectDisplayLabel.trim())) {
    return false;
  }
  return true;
}

function hasCustomerPayload(payload: RecordValue | null, aspectKeys: string[]): boolean {
  if (!payload) return false;
  if (payload.customer_label_schema_version === "1.0" || payload.specific_issue_schema_version === "1.0") {
    return true;
  }
  return getPayloadAspects(payload).some((aspect) => aspectKeys.some((key) => key in aspect));
}

function getPayloadAspects(payload: RecordValue): RecordValue[] {
  const aspects = payload.aspects;
  return Array.isArray(aspects)
    ? aspects.filter((item): item is RecordValue => Boolean(item) && typeof item === "object")
    : [];
}

export function customerIssueTags(comment: RecordValue, locale: string): string[] {
  const decorated = splitTagText(comment.customer_issue_tags);
  if (decorated.length > 0) {
    return uniqueStrings(decorated.filter((label) => isCustomerLabelAllowed(label, locale)));
  }

  const payload = parseAspectsPayload(comment);
  const aspects = getAspects(comment);
  const labels = aspects
    .filter((aspect) => {
      const hasSpecificIssuePayload = Boolean(aspect.specific_issue || aspect.specific_issue_zh) &&
        Boolean(aspect.canonical_issue_key);
      return (
        (String(aspect.polarity || "").toLowerCase() === "negative" || hasSpecificIssuePayload) &&
        aspect.display_allowed !== false &&
        hasSpecificIssuePayload
      );
    })
    .map((aspect) => {
      const aspectKey = String(aspect.key || aspect.aspect_key || "").trim();
      const label = String(
        locale.startsWith("zh")
          ? aspect.specific_issue_zh || aspect.specific_issue
          : aspect.specific_issue || aspect.specific_issue_zh,
      ).trim();
      return isCustomerLabelAllowed(label, locale, aspectKey, aspectLabel(aspectKey, locale)) ? label : "";
    })
    .filter(Boolean);

  if (labels.length > 0 || hasCustomerPayload(payload, ["specific_issue", "canonical_issue_key", "display_allowed"])) {
    return uniqueStrings(labels);
  }
  return uniqueStrings(splitTagText(comment.issue_tag).filter((label) => isCustomerLabelAllowed(label, locale)));
}

export function customerHighlightTags(comment: RecordValue, locale: string): string[] {
  const decorated = splitTagText(comment.customer_highlight_tags);
  if (decorated.length > 0) {
    return uniqueStrings(decorated.filter((label) => isCustomerLabelAllowed(label, locale)));
  }

  const payload = parseAspectsPayload(comment);
  const labels = getAspects(comment)
    .filter((aspect) => {
      return (
        String(aspect.polarity || "").toLowerCase() === "positive" &&
        aspect.highlight_display_allowed !== false &&
        Boolean(aspect.customer_highlight || aspect.customer_highlight_zh) &&
        Boolean(aspect.canonical_highlight_key)
      );
    })
    .map((aspect) => {
      const aspectKey = String(aspect.key || aspect.aspect_key || "").trim();
      const label = String(
        locale.startsWith("zh")
          ? aspect.customer_highlight_zh || aspect.customer_highlight
          : aspect.customer_highlight || aspect.customer_highlight_zh,
      ).trim();
      return isCustomerLabelAllowed(label, locale, aspectKey, aspectLabel(aspectKey, locale)) ? label : "";
    })
    .filter(Boolean);

  if (
    labels.length > 0 ||
    hasCustomerPayload(payload, ["customer_highlight", "canonical_highlight_key", "highlight_display_allowed"])
  ) {
    return uniqueStrings(labels);
  }
  return uniqueStrings(splitTagText(comment.highlight_tag).filter((label) => isCustomerLabelAllowed(label, locale)));
}

export function customerTagText(
  comment: RecordValue,
  type: "issue" | "highlight",
  locale: string,
): string {
  const labels = type === "issue" ? customerIssueTags(comment, locale) : customerHighlightTags(comment, locale);
  return labels.join(", ");
}
