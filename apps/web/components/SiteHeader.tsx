import { GitHubIcon, LabelIcon } from "./icons";

export const REPO = "https://github.com/s4natk/doodleverse";

const SECTIONS = [
  { href: "#play", label: "Play" },
  { href: "#how", label: "How it works" },
  { href: "#model", label: "Under the hood" },
];

export function Logo() {
  return (
    <span className="grid size-8 place-items-center rounded-xl bg-gradient-warm text-white shadow-[0_6px_16px_-6px_rgba(236,106,76,0.8)]">
      <LabelIcon label="sun" width={18} height={18} strokeWidth={2.2} />
    </span>
  );
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-paper/75 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
        <a href="#top" className="flex items-center gap-2.5 font-display text-lg font-semibold tracking-tight">
          <Logo />
          Doodleverse
        </a>
        <nav className="hidden flex-1 justify-center gap-8 text-sm text-muted md:flex" aria-label="Sections">
          {SECTIONS.map((section) => (
            <a key={section.href} href={section.href} className="transition hover:text-ink">
              {section.label}
            </a>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1.5 md:ml-0">
          <a
            href={REPO}
            className="rounded-full p-2 text-muted transition hover:bg-black/5 hover:text-ink"
            aria-label="Source on GitHub"
          >
            <GitHubIcon />
          </a>
          <a
            href="#play"
            className="rounded-full bg-gradient-warm px-4 py-2 text-sm font-semibold text-white shadow-[0_8px_20px_-8px_rgba(236,106,76,0.8)] transition hover:brightness-105"
          >
            Start drawing
          </a>
        </div>
      </div>
    </header>
  );
}
