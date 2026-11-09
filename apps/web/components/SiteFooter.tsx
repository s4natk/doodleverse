import { Logo, REPO } from "./SiteHeader";

const LINK = "font-semibold text-ink decoration-marker decoration-2 underline-offset-4 hover:underline";

export function SiteFooter() {
  return (
    <footer className="border-t-2 border-ink bg-sheet">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-graphite sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="flex items-center gap-3">
          <Logo />
          <span className="font-hand text-2xl leading-none text-ink">
            drawn by{" "}
            <a href="https://www.sanatkanwal.com" className="decoration-marker decoration-2 underline-offset-4 hover:underline">
              Sanat Kanwal
            </a>
          </span>
        </p>
        <p className="max-w-xl sm:text-right">
          Recognized by a model trained on{" "}
          <a href="https://github.com/googlecreativelab/quickdraw-dataset" className={LINK}>
            Quick, Draw!
          </a>{" "}
          by Google Creative Lab, used under CC BY 4.0.{" "}
          <a href={REPO} className={LINK}>
            Source on GitHub
          </a>
          .
        </p>
      </div>
    </footer>
  );
}
