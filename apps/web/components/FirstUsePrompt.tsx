import { at } from "../lib/motion";
import { PROMPTS, type FirstUse } from "../lib/onboarding";

const STEP: Record<Exclude<FirstUse, "done">, string> = { sun: "1/3", cloud: "2/3", anything: "3/3" };

export function FirstUsePrompt({ step }: { step: FirstUse | null }) {
  const text = step && step !== "done" ? PROMPTS[step] : null;
  return (
    <div className="pointer-events-none absolute inset-x-0 top-3 z-20 flex justify-center px-3" aria-live="polite">
      {text ? (
        <p
          key={step}
          className="pop flex max-w-full -rotate-1 items-baseline gap-2 rounded-md border-2 border-ink bg-note px-3 py-1 shadow-ink-sm"
          style={at(0.25)}
        >
          <span className="font-hand text-lg font-bold text-marker">{STEP[step as Exclude<FirstUse, "done">]}</span>
          <span className="font-hand text-xl leading-tight">{text}</span>
        </p>
      ) : null}
    </div>
  );
}
