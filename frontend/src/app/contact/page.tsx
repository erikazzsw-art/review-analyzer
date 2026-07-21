import { buildMarketingMetadata } from "@/lib/seo";

import { ContactForm } from "./contact-form";

export const metadata = buildMarketingMetadata({
  title: "联系我们",
  description:
    "对隐私政策有疑问？想了解产品功能？或者只是想 say hi？联系 ClueAI 团队，我们会在 24 小时内回复。",
  path: "/contact",
});

export default function ContactPage() {
  return <ContactForm />;
}
