"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, type ComponentProps, type MouseEvent } from "react";

import { motionAllowed, turnPage, type TurnDirection } from "../lib/pageTurn";

type Props = Omit<ComponentProps<typeof Link>, "href"> & { href: string; direction?: TurnDirection };

/** A link that turns the page like a sheet of paper before it navigates. A plain link with reduced motion. */
export function PageTurnLink({ href, direction = "forward", onClick, ...props }: Props) {
  const router = useRouter();

  useEffect(() => {
    router.prefetch(href);
  }, [router, href]);

  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    onClick?.(event);
    const modified = event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0;
    if (event.defaultPrevented || modified || !motionAllowed()) {
      return;
    }
    event.preventDefault();
    turnPage(direction).then(() => router.push(href));
  }

  return <Link href={href} onClick={handleClick} {...props} />;
}
