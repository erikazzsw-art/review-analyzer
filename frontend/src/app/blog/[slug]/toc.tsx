"use client";

import { useEffect, useState, useCallback } from "react";

/* ================================================================
   Blog TOC — 从文章 sections 中提取 h2 标题，支持滚动监听高亮
   ================================================================ */

interface TocHeading {
  id: string;
  text: string;
}

interface BlogTocProps {
  article: {
    sections: Array<{
      type: string;
      id?: string;
      text?: string;
    }>;
  };
}

export function BlogToc({ article }: BlogTocProps) {
  /* 从 article.sections 中提取所有 h2 标题 */
  const headings: TocHeading[] = article.sections
    .filter((s) => s.type === "h2" && s.id && s.text)
    .map((s) => ({ id: s.id!, text: s.text! }));

  const [activeId, setActiveId] = useState<string>("");

  /* IntersectionObserver 检测当前可见的 heading */
  const handleScroll = useCallback(() => {
    if (headings.length === 0) return;

    /* 从后往前找第一个 top <= 100px 的 heading */
    let current = "";
    for (let i = headings.length - 1; i >= 0; i--) {
      const el = document.getElementById(headings[i].id);
      if (el) {
        const rect = el.getBoundingClientRect();
        if (rect.top <= 120) {
          current = headings[i].id;
          break;
        }
      }
    }
    setActiveId(current);
  }, [headings]);

  useEffect(() => {
    if (headings.length === 0) return;

    /* 初始检测 */
    handleScroll();

    /* 使用 IntersectionObserver 作为主要检测手段 */
    const observer = new IntersectionObserver(
      (entries) => {
        /* 找到第一个进入视口上方的 heading */
        let topMostId = "";
        let topMostY = Infinity;

        /* 同时检查所有 heading 的位置 */
        for (const heading of headings) {
          const el = document.getElementById(heading.id);
          if (el) {
            const rect = el.getBoundingClientRect();
            if (rect.top <= 120 && rect.top < topMostY) {
              topMostY = rect.top;
              topMostId = heading.id;
            }
          }
        }
        if (topMostId) {
          setActiveId(topMostId);
        }
      },
      {
        rootMargin: "-10% 0px -70% 0px",
        threshold: 0,
      },
    );

    /* 观察所有 h2 元素 */
    const elements: Element[] = [];
    headings.forEach((h) => {
      const el = document.getElementById(h.id);
      if (el) {
        observer.observe(el);
        elements.push(el);
      }
    });

    /* fallback：scroll 事件兜底 */
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", handleScroll);
    };
  }, [headings, handleScroll]);

  /* 点击跳转到对应标题 */
  const scrollToHeading = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      /* 更新 URL hash 但不触发页面滚动 */
      window.history.replaceState(null, "", `#${id}`);
    }
  };

  if (headings.length === 0) return null;

  return (
    <div className="glass-white p-4">
      <h3 className="mb-3 font-heading text-sm font-bold uppercase tracking-[0.06em] text-ink">
        目录
      </h3>
      <nav>
        <ul className="flex flex-col gap-1">
          {headings.map((h) => {
            const isActive = h.id === activeId;
            return (
              <li key={h.id}>
                <button
                  type="button"
                  onClick={() => scrollToHeading(h.id)}
                  className={`flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left font-body text-[13px] leading-snug transition-colors duration-200 ${
                    isActive
                      ? "font-semibold text-rose"
                      : "text-soft hover:text-ink"
                  }`}
                >
                  {/* Active 指示点 */}
                  <span
                    className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full transition-colors duration-200 ${
                      isActive ? "bg-rose" : "bg-line"
                    }`}
                  />
                  <span className="line-clamp-2">{h.text}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
