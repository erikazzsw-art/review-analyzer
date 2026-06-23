"use client";

import { useEffect, useState, useCallback } from "react";

export type SectionItem = {
  id: string;
  label: string;
};

type Props = {
  sections: SectionItem[];
  offsetTop?: number;
};

export function SectionAnchorNav({ sections, offsetTop = 110 }: Props) {
  const [active, setActive] = useState<string>(sections[0]?.id || "");

  useEffect(() => {
    if (sections.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target?.id) {
          setActive(visible.target.id);
        }
      },
      {
        rootMargin: "-30% 0px -55% 0px",
        threshold: [0, 0.25, 0.5, 0.75, 1],
      },
    );

    sections.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [sections]);

  const handleJump = useCallback(
    (id: string) => {
      const el = document.getElementById(id);
      if (!el) return;
      const y = el.getBoundingClientRect().top + window.scrollY - offsetTop;
      window.scrollTo({ top: y, behavior: "smooth" });
      setActive(id);
    },
    [offsetTop],
  );

  return (
    <nav className="sticky top-[68px] z-20 -mx-4 flex gap-1 overflow-x-auto border-b border-line bg-white/95 px-4 backdrop-blur lg:-mx-6 lg:px-6">
      {sections.map((s) => {
        const isActive = active === s.id;
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => handleJump(s.id)}
            className={`relative shrink-0 px-4 py-3 text-sm font-semibold transition-colors ${
              isActive ? "text-rose" : "text-soft hover:text-ink"
            }`}
          >
            {s.label}
            <span
              className={`absolute inset-x-3 bottom-0 h-[2px] origin-left rounded-full bg-rose transition-transform ${
                isActive ? "scale-x-100" : "scale-x-0"
              }`}
            />
          </button>
        );
      })}
    </nav>
  );
}
