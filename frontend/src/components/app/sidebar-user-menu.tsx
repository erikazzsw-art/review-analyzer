"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronUp, LogOut, Settings, User } from "lucide-react";
import { useTranslations } from "next-intl";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type SidebarUserMenuProps = {
  username: string | null;
  plan: string | null;
};

export function SidebarUserMenu({ username, plan }: SidebarUserMenuProps) {
  const t = useTranslations("sidebar");
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);

  const displayName = username || t("notLoggedIn");

  async function handleLogout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // 即使后端报错也强制跳转登录页
    } finally {
      window.location.href = "/login";
    }
  }

  function handleSettings() {
    router.push("/settings");
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition hover:bg-roseSoft/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose/50"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-lavender/10 text-lavender">
            <User size={16} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-ink">
              {displayName}
            </div>
            {plan && <div className="text-xs text-soft">{plan}</div>}
          </div>
          <ChevronUp className="h-4 w-4 text-soft" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        side="top"
        sideOffset={8}
        className="w-[220px] rounded-xl border border-line bg-white p-1 shadow-card"
      >
        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault();
            handleSettings();
          }}
          className="cursor-pointer gap-2 rounded-md px-3 py-2 text-sm text-ink hover:bg-roseSoft/50 focus:bg-roseSoft/50"
        >
          <Settings className="h-4 w-4 text-soft" />
          <span>{t("systemSettings")}</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator className="my-1 h-px bg-line" />
        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault();
            handleLogout();
          }}
          disabled={loggingOut}
          className="cursor-pointer gap-2 rounded-md px-3 py-2 text-sm text-rose hover:bg-rose/10 focus:bg-rose/10"
        >
          <LogOut className="h-4 w-4" />
          <span>{loggingOut ? t("loggingOut") : t("logout")}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
