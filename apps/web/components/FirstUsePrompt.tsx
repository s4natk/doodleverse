import { PROMPTS, type FirstUse } from "../lib/onboarding";
import { SparkIcon } from "./icons";

const STEP: Record<Exclude<FirstUse, "done">, string> = { sun: "1/3", cloud: "2/3", anything: "3/3" };

export function FirstUsePrompt({ step }: { step: FirstUse | null }) {
  const text = step && step !== "done" ? PROMPTS[step] : null;
  return (
    <div className="pointer-events-none absolute inset-x-0 top-3 flex justify-center px-3" aria-live="polite">
      {text ? (
        <p
          key={step}
          className="flex max-w-full items-center gap-2 rounded-full bg-ink/80 py-2 pl-2 pr-4 text-sm text-white shadow-lg backdrop-blur-sm"
        >
          <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2 py-0.5 text-xs font-medium tabular-nums">
            <SparkIcon width={12} height={12} />
            {STEP[step as Exclude<FirstUse, "done">]}
          </span>
          <span>{text}</span>
        </p>
      ) : null}
    </div>
  );
}
