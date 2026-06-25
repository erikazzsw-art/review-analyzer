"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/settings/push", label: "绑定飞书" },
  { href: "/settings/api-keys", label: "API 密钥" },
  { href: "/settings/billing", label: "订阅计费" },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-[calc(100vh-4rem)] gap-0">
      <aside className="w-48 shrink-0 border-r border-line bg-white/60 px-3 py-6">
        <h2 className="mb-4 px-3 text-xs font-bold uppercase tracking-widest text-soft">
          系统设置
        </h2>
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
                pathname === item.href
                  ? "bg-ink/5 text-ink"
                  : "text-soft hover:bg-ink/3 hover:text-ink",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto px-6 py-4">{children}</main>
    </div>
  );
}
