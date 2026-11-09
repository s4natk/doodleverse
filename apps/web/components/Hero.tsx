import { LABELS } from "../lib/contract";
import { ArrowDownIcon, LabelIcon } from "./icons";
import { LABEL_COLOR } from "./labelColors";

export function Hero() {
  return (
    <section id="top" className="mx-auto max-w-6xl px-4 pb-8 pt-10 text-center sm:px-6 sm:pt-14">
      <p className="inline-flex items-center gap-2 rounded-full border border-line bg-white/70 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-muted">
        <span className="size-1.5 rounded-full bg-coral" />
        Trained on Quick, Draw!
      </p>
      <h1 className="mx-auto mt-5 max-w-4xl font-display text-5xl font-bold leading-[1.04] tracking-tight sm:text-6xl lg:text-7xl">
        Draw it. <span className="text-gradient">Bring it to life.</span>
      </h1>
      <p className="mx-auto mt-5 max-w-2xl text-base text-muted sm:text-lg">
        Sketch one thing and a small CNN trained on Quick, Draw! names it. Confirm, and it moves into a world that
        answers back: suns bring daylight, tapped clouds rain, trees grow, and cats keep clear of cars.
      </p>
      <ul className="mt-6 flex flex-wrap justify-center gap-2" aria-label="What it can recognize">
        {LABELS.map((label) => (
          <li
            key={label}
            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white/80 px-3 py-1.5 text-sm capitalize shadow-[0_1px_0_rgba(0,0,0,0.03)]"
          >
            <LabelIcon label={label} className={LABEL_COLOR[label]} width={16} height={16} />
            {label}
          </li>
        ))}
      </ul>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <a
          href="#play"
          className="inline-flex items-center gap-2 rounded-full bg-gradient-warm px-6 py-3 font-display text-base font-semibold text-white shadow-[0_14px_30px_-12px_rgba(236,106,76,0.85)] transition hover:brightness-105"
        >
          Start drawing
          <ArrowDownIcon />
        </a>
        <a
          href="#how"
          className="inline-flex items-center rounded-full border border-line bg-white px-6 py-3 font-display text-base font-medium shadow-sm transition hover:border-black/15"
        >
          How it works
        </a>
      </div>
    </section>
  );
}
