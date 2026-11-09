import { LABELS } from "../lib/contract";
import { at } from "../lib/motion";
import { HeroSketch } from "./HeroSketch";
import { ArrowRightIcon, LabelIcon } from "./icons";
import { LABEL_COLOR } from "./labelColors";
import { PageTurnLink } from "./PageTurnLink";

const TILT = ["-rotate-3", "rotate-2", "-rotate-1", "rotate-3", "-rotate-2", "rotate-1"];

export function Hero() {
  return (
    <section
      id="top"
      className="mx-auto grid max-w-6xl items-center gap-14 px-4 pb-20 pt-10 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:pt-16"
    >
      <div>
        <p className="ink-write font-hand text-2xl text-graphite" style={at(0.05, 0.6)}>
          a sketchbook that draws back
        </p>
        <h1 className="mt-1 font-display text-6xl font-extrabold leading-[0.95] tracking-tight sm:text-7xl lg:text-[5.5rem]">
          <span className="ink-write block" style={at(0.2, 0.6)}>
            Draw it.
          </span>
          <span className="ink-write block" style={at(0.7, 0.8)}>
            Bring it to{" "}
            <span className="highlight" style={at(1.45)}>
              life.
            </span>
          </span>
        </h1>
        <p className="fade mt-6 max-w-xl text-lg leading-relaxed text-graphite" style={at(1.2)}>
          Sketch one thing and a small CNN trained on Quick, Draw! names it. Confirm, and your drawing moves into a world
          that reacts: suns bring daylight, tapped clouds rain, trees grow, and cats keep clear of cars.
        </p>
        <ul className="mt-7 flex flex-wrap gap-2.5" aria-label="What it can recognize">
          {LABELS.map((label, index) => (
            <li
              key={label}
              className={`pop ${TILT[index]} inline-flex items-center gap-1.5 rounded-full border-2 border-ink bg-sheet px-3 py-1.5 text-sm font-semibold capitalize shadow-ink-sm`}
              style={at(1.5 + index * 0.07)}
            >
              <LabelIcon label={label} className={LABEL_COLOR[label]} width={16} height={16} strokeWidth={2.2} />
              {label}
            </li>
          ))}
        </ul>
        <div className="mt-9 flex flex-wrap gap-4">
          <PageTurnLink href="/draw" className="btn-ink pop bg-marker px-6 py-3.5 text-lg text-white" style={at(2)}>
            Start drawing
            <ArrowRightIcon />
          </PageTurnLink>
          <a href="#how" className="btn-ink pop bg-sheet px-6 py-3.5 text-lg" style={at(2.1)}>
            How it works
          </a>
        </div>
      </div>
      <div className="relative">
        <div className="ink-card pop relative rotate-1 p-4 sm:p-6" style={at(0.25)}>
          <span className="tape -left-5 -top-3 -rotate-12" aria-hidden />
          <span className="tape -right-6 top-8 rotate-[14deg]" aria-hidden />
          <HeroSketch />
        </div>
        <p className="fade absolute -bottom-11 right-2 font-hand text-2xl text-graphite" style={at(5.2)}>
          yours will be messier. that is fine.
        </p>
      </div>
    </section>
  );
}
