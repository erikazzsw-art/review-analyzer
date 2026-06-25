"use client";

import { Bell } from "lucide-react";

export function AlertsTab() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-line py-16">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
        <Bell className="h-6 w-6 text-soft" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-ink">告警配置即将上线</h3>
      <p className="mt-2 max-w-sm text-center text-sm text-soft">
        配置错误率阈值、延迟告警和费用预警，当系统异常时自动通知
      </p>
      <button
        disabled
        className="mt-6 rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-soft"
      >
        开始配置
      </button>
    </div>
  );
}
