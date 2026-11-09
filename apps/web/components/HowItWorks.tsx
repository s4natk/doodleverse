import { at } from "../lib/motion";
import { Reveal } from "./Reveal";

const STEPS = [
  {
    title: "Draw",
    note: "mouse, pen, or finger",
    badge: "bg-lime",
    tilt: "-rotate-1",
    text: "Sketch one thing. Undo and the eraser are there when a line goes wrong.",
  },
  {
    title: "Recognize",
    note: "a CNN reads it",
    badge: "bg-[#cfdbff]",
    tilt: "rotate-1",
    text: "Your strokes go to a FastAPI service, which draws them at 28×28 exactly the way the training images were made, then asks a TensorFlow CNN.",
  },
  {
    title: "Confirm",
    note: "you get the last word",
    badge: "bg-note",
    tilt: "-rotate-1",
    text: "A confident answer takes one tap. A close call shows its top three and lets you choose. It never picks for you.",
  },
  {
    title: "Watch it live",
    note: "it reacts to the rest",
    badge: "bg-[#ffd0e0]",
    tilt: "rotate-1",
    text: "Suns light the sky, a tapped cloud rains, trees and flowers grow in it, cars drive and bump, cats wander off.",
  },
];

export function SectionHeading({ note, title, children }: { note: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="max-w-2xl">
      <p className="fade font-hand text-2xl text-marker">{note}</p>
      <h2 className="ink-write font-display text-5xl font-extrabold leading-[1.02] tracking-tight sm:text-6xl" style={at(0.1, 0.8)}>
        {title}
      </h2>
      {children ? (
        <p className="fade mt-4 text-lg text-graphite" style={at(0.5)}>
          {children}
        </p>
      ) : null}
    </div>
  );
}

export function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
      <Reveal>
        <SectionHeading note="how it works" title="How a scribble comes alive">
          Four steps, a couple of seconds, no account.
        </SectionHeading>
      </Reveal>
      <Reveal>
        <ol className="mt-16 grid gap-10 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
          {STEPS.map((step, index) => (
            <li key={step.title} className={`pop ink-card relative p-6 pt-9 ${step.tilt}`} style={at(0.1 + index * 0.15)}>
              <span
                className={`absolute -top-6 left-5 grid size-12 place-items-center rounded-full border-2 border-ink font-hand text-3xl font-bold shadow-ink-sm ${step.badge}`}
              >
                {index + 1}
              </span>
              <h3 className="font-display text-2xl font-extrabold tracking-tight">{step.title}</h3>
              <p className="font-hand text-xl leading-tight text-marker">{step.note}</p>
              <p className="mt-3 text-sm leading-relaxed text-graphite">{step.text}</p>
            </li>
          ))}
        </ol>
      </Reveal>
    </section>
  );
}
