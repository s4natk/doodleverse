import { PROMPTS, type FirstUse } from "../lib/onboarding";

export function FirstUsePrompt({ step }: { step: FirstUse | null }) {
  const text = step && step !== "done" ? PROMPTS[step] : null;
  return (
    <div className="pointer-events-none absolute inset-x-0 top-4 flex justify-center" aria-live="polite">
      {text ? (
        <p
          key={step}
          className="rounded-full bg-[#2c2733]/80 px-4 py-2 text-sm text-[#f3e6d4] shadow-lg backdrop-blur-sm"
        >
          {text}
        </p>
      ) : null}
    </div>
  );
}
