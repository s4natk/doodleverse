const STEPS = [
  {
    title: "Draw",
    tint: "bg-[#fde8e1] text-coral",
    text: "Sketch with a mouse, a pen, or a finger. Undo and the eraser are there when a line goes wrong.",
  },
  {
    title: "Recognize",
    tint: "bg-[#e4f0e2] text-leaf",
    text: "Your strokes go to a FastAPI service, which draws them at 28×28 exactly the way the training images were made, then asks a TensorFlow CNN.",
  },
  {
    title: "Confirm",
    tint: "bg-[#e3edfa] text-sky",
    text: "A confident answer takes one tap. A close call shows its top three and lets you choose. It never picks for you.",
  },
  {
    title: "Watch it live",
    tint: "bg-[#fdf0d8] text-[#c27a12]",
    text: "Suns light the sky, a tapped cloud rains, trees and flowers grow in it, cars drive and bump, cats wander off.",
  },
];

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mx-auto inline-flex items-center gap-2 rounded-full border border-line bg-white/70 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-muted">
      <span className="size-1.5 rounded-full bg-coral" />
      {children}
    </p>
  );
}

export function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-6xl px-4 py-24 text-center sm:px-6">
      <SectionLabel>How it works</SectionLabel>
      <h2 className="mt-4 font-display text-4xl font-bold tracking-tight sm:text-5xl">From a scribble to something alive</h2>
      <p className="mx-auto mt-4 max-w-xl text-muted">Four steps, a couple of seconds, no account.</p>
      <ol className="relative mt-14 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
        <span
          className="absolute left-[12.5%] right-[12.5%] top-7 hidden border-t-2 border-dashed border-line lg:block"
          aria-hidden
        />
        {STEPS.map((step, index) => (
          <li key={step.title} className="relative flex flex-col items-center">
            <span
              className={`grid size-14 place-items-center rounded-2xl font-display text-lg font-bold ring-4 ring-paper ${step.tint}`}
            >
              {String(index + 1).padStart(2, "0")}
            </span>
            <h3 className="mt-5 font-display text-xl font-semibold">{step.title}</h3>
            <p className="mt-2 max-w-64 text-sm leading-relaxed text-muted">{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
