export type TurnDirection = "forward" | "back";

/** Whether page turns and draw-ins run. The layout's script decides before paint. */
export function motionAllowed(): boolean {
  return document.documentElement.classList.contains("motion-ok");
}

/**
 * Turn the current page away like a sheet of paper, hinged on the left edge going forward and on the right going
 * back. The sheet is pinned where it is on screen first, so a scrolled page turns from where the visitor sees it.
 */
export function turnPage(direction: TurnDirection): Promise<void> {
  const sheet = document.getElementById("sheet");
  if (!sheet || !motionAllowed()) {
    return Promise.resolve();
  }
  const scrolled = window.scrollY;
  sheet.style.top = `${-scrolled}px`;
  sheet.style.transformOrigin = `${direction === "forward" ? "0" : "100%"} ${scrolled + window.innerHeight / 2}px`;
  sheet.dataset.turn = direction;
  return new Promise((resolve) => {
    const timer = window.setTimeout(resolve, 900);
    sheet.addEventListener(
      "animationend",
      (event) => {
        if (event.target === sheet) {
          window.clearTimeout(timer);
          resolve();
        }
      },
      { once: true },
    );
  });
}
