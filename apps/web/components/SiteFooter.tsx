import { Logo, REPO } from "./SiteHeader";

export function SiteFooter() {
  return (
    <footer className="border-t border-line/80 bg-white/40">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="flex items-center gap-2.5">
          <Logo />
          <span>
            Doodleverse, built by{" "}
            <a href="https://www.sanatkanwal.com" className="text-ink underline-offset-4 hover:underline">
              Sanat Kanwal
            </a>
          </span>
        </p>
        <p className="max-w-xl sm:text-right">
          Recognized by a model trained on{" "}
          <a
            href="https://github.com/googlecreativelab/quickdraw-dataset"
            className="text-ink underline-offset-4 hover:underline"
          >
            Quick, Draw!
          </a>{" "}
          by Google Creative Lab, used under CC BY 4.0.{" "}
          <a href={REPO} className="text-ink underline-offset-4 hover:underline">
            Source on GitHub
          </a>
          .
        </p>
      </div>
    </footer>
  );
}
