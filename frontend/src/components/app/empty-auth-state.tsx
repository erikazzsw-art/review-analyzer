import Link from "next/link";

type EmptyAuthStateProps = {
  title: string;
  description: string;
};

export function EmptyAuthState({
  title,
  description,
}: EmptyAuthStateProps) {
  return (
    <section className="rounded-shell border border-dashed border-line bg-white/78 px-6 py-10 text-center shadow-card backdrop-blur md:px-10">
      <div className="mx-auto max-w-2xl">
        <div className="inline-flex rounded-pill bg-roseSoft px-4 py-2 text-xs font-bold tracking-[0.12em] text-[#d94d72]">
          登录后可见增长数据
        </div>
        <h2 className="mt-5 font-heading text-3xl font-extrabold tracking-normal text-ink">
          {title}
        </h2>
        <p className="mt-4 text-base leading-8 text-soft">{description}</p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link
            href="/login"
            className="inline-flex min-h-11 items-center justify-center rounded-pill bg-ink px-5 py-3 text-sm font-semibold text-white shadow-card"
          >
            登录 ClueAI
          </Link>
          <Link
            href="/register"
            className="inline-flex min-h-11 items-center justify-center rounded-pill border border-line bg-white px-5 py-3 text-sm font-semibold text-ink"
          >
            免费创建账号
          </Link>
        </div>
      </div>
    </section>
  );
}
