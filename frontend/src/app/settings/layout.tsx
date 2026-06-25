"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import { Sidebar } from "@/components/app/sidebar";
import { FeedbackWidget } from "@/components/feedback/FeedbackWidget";

const NAV_ITEMS = [
  { href: "/settings/push", label: "绑定飞书" },
  { href: "/settings/api-keys", label: "API 密钥" },
  { href: "/settings/billing", label: "订阅计费" },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-hero-wash">
      <Sidebar currentPath="/settings" />

      <div className="pt-14 md:pl-[260px] md:pt-0">
        <header className="px-6 pb-1 pt-6 lg:px-10">
          <h1 className="font-heading text-2xl font-extrabold tracking-[-0.03em] text-ink md:text-3xl">
            系统设置
          </h1>
          <p className="mt-1.5 text-sm leading-6 text-soft md:text-base">
            管理推送、API 密钥和订阅计划。
          </p>
        </header>

        <div className="px-6 pt-4 lg:px-10">
          <nav className="mb-6 flex gap-1 border-b border-line">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "relative px-4 py-2.5 text-sm font-medium transition-colors",
                  pathname === item.href
                    ? "text-ink"
                    : "text-soft hover:text-ink",
                )}
              >
                {item.label}
                {pathname === item.href && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-rose" />
                )}
              </Link>
            ))}
          </nav>

          {children}
        </div>
      </div>

      <FeedbackWidget />
    </div>
  );
}
