"use client";

type EmptyDataNoticeProps = {
  title: string;
  description: string;
  action: string;
};

export function EmptyDataNotice({ title, description, action }: EmptyDataNoticeProps) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-gray-50 p-4">
      <div className="text-sm font-medium text-ink">{title}</div>
      <p className="mt-1 text-sm text-soft">{description}</p>
      <p className="mt-2 text-xs font-medium text-soft">下一步：{action}</p>
    </div>
  );
}
