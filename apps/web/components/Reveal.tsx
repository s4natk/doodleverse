"use client";

import { useEffect, useRef, type ReactNode } from "react";

type Props = { children: ReactNode; id?: string; className?: string; as?: "div" | "section" };

/** Holds the draw-in animations inside until the block scrolls into view, then lets them play once. */
export function Reveal({ children, id, className, as: Tag = "div" }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) {
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          node.dataset.shown = "true";
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -12% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <Tag ref={ref} id={id} className={className} data-reveal>
      {children}
    </Tag>
  );
}
