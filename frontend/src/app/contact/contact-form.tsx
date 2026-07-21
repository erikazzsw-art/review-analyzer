"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Mail, Clock, Send } from "lucide-react";

import { MarketingShell } from "@/components/marketing/marketing-shell";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type SubjectChannel = "privacy" | "support" | "hello";

const SUBJECTS: readonly SubjectChannel[] = ["privacy", "support", "hello"] as const;

function WorldMapDots() {
  return (
    <svg
      viewBox="0 0 800 400"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="h-auto w-full"
      aria-hidden="true"
    >
      {/* Continent outlines — simplified stylized paths */}
      <g
        stroke="rgba(243,111,143,0.18)"
        strokeWidth="1.2"
        strokeDasharray="6 8"
        strokeLinecap="round"
        fill="none"
      >
        {/* North America */}
        <path d="M120,60 Q160,30 200,50 Q240,35 270,55 Q300,40 320,65 Q310,90 330,110 Q320,140 290,150 Q260,170 240,200 Q210,220 180,210 Q150,195 140,160 Q110,130 120,60Z" />
        {/* South America */}
        <path d="M200,230 Q230,220 250,240 Q270,260 260,290 Q250,330 230,350 Q210,340 200,310 Q190,280 200,230Z" />
        {/* Europe */}
        <path d="M370,55 Q390,40 420,45 Q450,38 470,50 Q490,55 480,80 Q470,100 450,110 Q420,120 400,105 Q380,90 370,55Z" />
        {/* Africa */}
        <path d="M390,130 Q420,115 450,125 Q480,140 490,170 Q500,210 480,250 Q450,280 420,270 Q400,250 390,210 Q380,170 390,130Z" />
        {/* Asia */}
        <path d="M500,40 Q540,30 580,38 Q620,35 660,45 Q700,50 730,60 Q740,90 720,110 Q700,130 680,120 Q650,140 620,135 Q580,145 540,130 Q510,110 500,80 Q490,55 500,40Z" />
        {/* Southeast Asia / Indonesia */}
        <path d="M680,120 Q710,115 730,130 Q725,150 710,155 Q690,148 680,120Z" />
        <path d="M700,160 Q720,155 740,165 Q735,180 715,175 Q700,170 700,160Z" />
        {/* Australia */}
        <path d="M650,240 Q690,230 720,245 Q740,265 720,290 Q690,295 660,280 Q640,260 650,240Z" />
        {/* Japan */}
        <path d="M740,70 Q755,65 760,80 Q755,100 740,95 Q735,80 740,70Z" />
        {/* Greenland */}
        <path d="M320,30 Q340,20 350,30 Q345,50 330,55 Q315,45 320,30Z" />
        {/* UK / Ireland */}
        <path d="M355,50 Q365,42 370,55 Q365,70 355,65 Q348,55 355,50Z" />
        {/* Madagascar */}
        <path d="M500,270 Q510,265 515,280 Q510,300 498,290 Q495,278 500,270Z" />
        {/* New Zealand */}
        <path d="M760,300 Q770,295 772,308 Q768,320 758,315 Q755,305 760,300Z" />
      </g>
      {/* Decorative dots at major city locations */}
      <g fill="rgba(243,111,143,0.35)">
        <circle cx="180" cy="110" r="3" />
        <circle cx="230" cy="130" r="2.5" />
        <circle cx="200" cy="270" r="2.5" />
        <circle cx="420" cy="70" r="3" />
        <circle cx="450" cy="65" r="2.5" />
        <circle cx="430" cy="180" r="2.5" />
        <circle cx="580" cy="55" r="3" />
        <circle cx="650" cy="75" r="2.5" />
        <circle cx="700" cy="70" r="2.5" />
        <circle cx="690" cy="255" r="2.5" />
        <circle cx="350" cy="48" r="2.5" />
        <circle cx="510" cy="280" r="2" />
      </g>
      {/* Subtle grid lines */}
      <g stroke="rgba(0,0,0,0.04)" strokeWidth="0.5">
        <line x1="0" y1="100" x2="800" y2="100" />
        <line x1="0" y1="200" x2="800" y2="200" />
        <line x1="0" y1="300" x2="800" y2="300" />
        <line x1="200" y1="0" x2="200" y2="400" />
        <line x1="400" y1="0" x2="400" y2="400" />
        <line x1="600" y1="0" x2="600" y2="400" />
      </g>
    </svg>
  );
}

export function ContactForm() {
  const t = useTranslations("contact");
  const [form, setForm] = useState({
    name: "",
    email: "",
    subject: "" as SubjectChannel | "",
    message: "",
  });
  const [sending, setSending] = useState(false);

  const handleChange = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);
    // TODO: wire to backend contact API
    await new Promise((r) => setTimeout(r, 800));
    setSending(false);
    alert(t("form.sent"));
    setForm({ name: "", email: "", subject: "", message: "" });
  };

  return (
    <MarketingShell title={t("title")} description={t("description")}>
      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* ── Left 50%: Contact Form ── */}
          <div className="glass-white p-6 md:p-8">
            <h2 className="mb-6 font-heading text-xl font-bold tracking-[-0.02em] text-ink">
              {t("form.title")}
            </h2>
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {/* Name */}
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="contact-name"
                  className="text-sm font-medium text-ink/80"
                >
                  {t("form.name")}
                </label>
                <Input
                  id="contact-name"
                  required
                  placeholder={t("form.namePlaceholder")}
                  value={form.name}
                  onChange={(e) => handleChange("name", e.target.value)}
                  className="h-11 rounded-xl border-line bg-white/50"
                />
              </div>

              {/* Email */}
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="contact-email"
                  className="text-sm font-medium text-ink/80"
                >
                  {t("form.email")}
                </label>
                <Input
                  id="contact-email"
                  type="email"
                  required
                  placeholder={t("form.emailPlaceholder")}
                  value={form.email}
                  onChange={(e) => handleChange("email", e.target.value)}
                  className="h-11 rounded-xl border-line bg-white/50"
                />
              </div>

              {/* Subject */}
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="contact-subject"
                  className="text-sm font-medium text-ink/80"
                >
                  {t("form.subject")}
                </label>
                <Select
                  value={form.subject}
                  onValueChange={(v) => handleChange("subject", v)}
                >
                  <SelectTrigger
                    id="contact-subject"
                    className="h-11 rounded-xl border-line bg-white/50"
                  >
                    <SelectValue placeholder={t("form.subjectPlaceholder")} />
                  </SelectTrigger>
                  <SelectContent>
                    {SUBJECTS.map((ch) => (
                      <SelectItem key={ch} value={ch}>
                        {t(`${ch}.label`)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Message */}
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="contact-message"
                  className="text-sm font-medium text-ink/80"
                >
                  {t("form.message")}
                </label>
                <Textarea
                  id="contact-message"
                  required
                  rows={5}
                  placeholder={t("form.messagePlaceholder")}
                  value={form.message}
                  onChange={(e) => handleChange("message", e.target.value)}
                  className="resize-none rounded-xl border-line bg-white/50"
                />
              </div>

              {/* Submit */}
              <Button
                type="submit"
                variant="marketing"
                size="marketing"
                disabled={sending}
                className="mt-2 w-full"
              >
                {sending ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    {t("form.sending")}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2">
                    <Send className="h-4 w-4" />
                    {t("form.submit")}
                  </span>
                )}
              </Button>
            </form>
          </div>

          {/* ── Right 50%: Info Cards + Map ── */}
          <div className="flex flex-col gap-4">
            {/* Info Cards Row */}
            <div className="grid gap-4 sm:grid-cols-2">
              {/* Email Card */}
              <div className="glass-white flex flex-col gap-3 p-5">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-roseSoft text-[#d94d72]">
                  <Mail className="h-5 w-5" />
                </span>
                <div>
                  <h3 className="font-heading text-sm font-bold text-ink">
                    {t("info.emailTitle")}
                  </h3>
                  <a
                    href="mailto:support@clueai-reviewlens.com"
                    className="mt-1 block break-all text-sm text-soft underline decoration-dotted underline-offset-4 hover:text-[#f36f8f]"
                  >
                    support@clueai-reviewlens.com
                  </a>
                </div>
              </div>

              {/* Reply Time Card */}
              <div className="glass-white flex flex-col gap-3 p-5">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[#4fb99f]/10 text-[#4fb99f]">
                  <Clock className="h-5 w-5" />
                </span>
                <div>
                  <h3 className="font-heading text-sm font-bold text-ink">
                    {t("info.replyTitle")}
                  </h3>
                  <p className="mt-1 text-sm text-soft">
                    {t("responseTime")}
                  </p>
                </div>
              </div>
            </div>

            {/* Decorative World Map */}
            <div className="glass-white overflow-hidden p-4">
              <WorldMapDots />
            </div>
          </div>
        </div>
      </div>
    </MarketingShell>
  );
}
