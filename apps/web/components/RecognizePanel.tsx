"use client";

import { LABELS, type Label } from "../lib/contract";
import type { Prediction } from "../lib/inference";
import type { Flow } from "../lib/studio";

type Props = {
  flow: Flow;
  canRecognize: boolean;
  mocked: boolean;
  onRecognize: () => void;
  onConfirm: () => void;
  onPick: (label: Label) => void;
  onRetry: () => void;
  onRevise: () => void;
};

const PRIMARY =
  "w-full rounded-full bg-[#2c2733] px-4 py-2.5 font-medium text-[#f3e6d4] transition hover:bg-[#40394a] " +
  "disabled:cursor-not-allowed disabled:opacity-40";
const SECONDARY = "rounded-full bg-white/80 px-3 py-1.5 text-sm transition hover:bg-white";

function TopThree({ prediction, onPick }: { prediction: Prediction; onPick: (label: Label) => void }) {
  return (
    <ul className="flex flex-col gap-1.5" aria-label="Top three guesses">
      {prediction.top3.map((guess) => (
        <li key={guess.label}>
          <button
            type="button"
            className="group flex w-full items-center gap-3 rounded-xl bg-white/80 px-3 py-2 text-left transition hover:bg-white"
            onClick={() => onPick(guess.label)}
          >
            <span className="w-14 capitalize">{guess.label}</span>
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-black/10">
              <span className="block h-full rounded-full bg-[#9a6b58]" style={{ width: `${guess.score * 100}%` }} />
            </span>
            <span className="w-10 text-right text-xs tabular-nums text-black/50">{guess.score.toFixed(2)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function AllSix({ onPick }: { onPick: (label: Label) => void }) {
  return (
    <div>
      <p className="mb-2 text-sm text-black/60">Something else?</p>
      <div className="grid grid-cols-3 gap-1.5">
        {LABELS.map((label) => (
          <button key={label} type="button" className={`${SECONDARY} capitalize`} onClick={() => onPick(label)}>
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function RecognizePanel({ flow, canRecognize, mocked, onRecognize, onConfirm, onPick, onRetry, onRevise }: Props) {
  const keepDrawing = (
    <button type="button" className={`${SECONDARY} self-start`} onClick={onRevise}>
      Keep drawing
    </button>
  );

  return (
    <section className="flex flex-col gap-4 rounded-2xl bg-white/50 p-5" aria-live="polite" aria-busy={flow.kind === "recognizing"}>
      {mocked ? (
        <p className="self-start rounded-full bg-[#9a6b58]/15 px-2.5 py-0.5 text-xs text-[#7d5242]">Mock recognizer</p>
      ) : null}

      {flow.kind === "drawing" || flow.kind === "recognizing" ? (
        <>
          <div>
            <h2 className="text-xl font-semibold">What did you draw?</h2>
            <p className="mt-1 text-sm text-black/60">Finish the drawing, then ask.</p>
          </div>
          <button type="button" className={PRIMARY} disabled={!canRecognize} onClick={onRecognize}>
            {flow.kind === "recognizing" ? "Recognizing…" : "Recognize"}
          </button>
        </>
      ) : null}

      {flow.kind === "suggested" ? (
        <>
          <h2 className="text-xl font-semibold">Looks like a {flow.prediction.label}.</h2>
          <button type="button" className={PRIMARY} onClick={onConfirm}>
            Yes, it&apos;s a {flow.prediction.label}
          </button>
          <TopThree prediction={flow.prediction} onPick={onPick} />
          <AllSix onPick={onPick} />
          {keepDrawing}
        </>
      ) : null}

      {flow.kind === "choosing" ? (
        <>
          <div>
            <h2 className="text-xl font-semibold">Not sure. Which one is it?</h2>
            <p className="mt-1 text-sm text-black/60">The top guesses are too close to call, so nothing is picked for you.</p>
          </div>
          <TopThree prediction={flow.prediction} onPick={onPick} />
          <AllSix onPick={onPick} />
          {keepDrawing}
        </>
      ) : null}

      {flow.kind === "failed" ? (
        <>
          <div>
            <h2 className="text-xl font-semibold">That didn&apos;t work.</h2>
            <p className="mt-1 text-sm text-black/60">{flow.error.message}</p>
          </div>
          <button type="button" className={PRIMARY} onClick={onRetry}>
            Try again
          </button>
          {keepDrawing}
        </>
      ) : null}
    </section>
  );
}
