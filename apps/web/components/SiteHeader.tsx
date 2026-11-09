import { ArrowLeftIcon, GitHubIcon, LabelIcon } from "./icons";
import { PageTurnLink } from "./PageTurnLink";

export const REPO = "https://github.com/s4natk/doodleverse";

const NAV = "font-semibold decoration-marker decoration-[3px] underline-offset-[6px] transition hover:underline";

export function Logo() {
  return (
    <span className="grid size-9 place-items-center rounded-[10px] border-2 border-ink bg-marker text-white shadow-ink-sm">
      <LabelIcon label="sun" width={19} height={19} strokeWidth={2.4} />
    </span>
  );
}

function Wordmark() {
  return <span className="font-display text-xl font-extrabold tracking-tight">Doodleverse</span>;
}

function GitHubLink() {
  return (
    <a
      href={REPO}
      className="rounded-lg border-2 border-transparent p-1.5 transition hover:border-ink hover:bg-lime"
      aria-label="Source on GitHub"
    >
      <GitHubIcon />
    </a>
  );
}

const BAR = "sticky top-0 z-30 border-b-2 border-ink bg-paper/90 backdrop-blur";

/** The cover's header. */
export function SiteHeader() {
  return (
    <header className={BAR}>
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
        <a href="#top" className="flex items-center gap-2.5">
          <Logo />
          <Wordmark />
        </a>
        <nav className="hidden flex-1 justify-center gap-8 text-sm md:flex" aria-label="Sections">
          <a href="#how" className={NAV}>
            How it works
          </a>
          <a href="#model" className={NAV}>
            The model
          </a>
        </nav>
        <div className="ml-auto flex items-center gap-2 md:ml-0">
          <GitHubLink />
          <span className="hidden sm:inline-flex">
            <PageTurnLink href="/draw" className="btn-ink bg-marker px-4 py-2 text-sm text-white">
              Start drawing
            </PageTurnLink>
          </span>
        </div>
      </div>
    </header>
  );
}

/** The sketchbook's header: back to the cover, with the page turning the other way. */
export function DrawHeader() {
  return (
    <header className={BAR}>
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <PageTurnLink href="/" direction="back" className="btn-ink bg-sheet px-3 py-1.5 text-sm">
          <ArrowLeftIcon width={16} height={16} />
          Cover
        </PageTurnLink>
        <span className="flex items-center gap-2.5">
          <Logo />
          <span className="hidden sm:inline">
            <Wordmark />
          </span>
        </span>
        <div className="ml-auto">
          <GitHubLink />
        </div>
      </div>
    </header>
  );
}
