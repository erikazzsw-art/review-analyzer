import { buildMarketingMetadata } from "@/lib/seo";

import { SubProcessorsContent } from "./sub-processors-content";

export const metadata = buildMarketingMetadata({
  title: "子处理者名单 — 数据合规",
  description:
    "ClueAI ReviewLens 使用的第三方子处理者（Sub-processors）清单，包括数据库、CDN、支付、AI 推理等服务商及其用途和处理地区。",
  path: "/sub-processors",
});

export default function SubProcessorsPage() {
  return <SubProcessorsContent />;
}
