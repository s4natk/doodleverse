"use client";

import { LABELS, type Label } from "../lib/contract";
import type { Prediction } from "../lib/inference";
import { at } from "../lib/motion";
import type { Flow } from "../lib/studio";
import { LabelIcon, SparkIcon } from "./icons";
import { LABEL_COLOR } from "./labelColors";

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

const PRIMARY = "btn-ink w-full bg-marker px-5 py-3 text-base text-white";
const QUIET =
  "self-start text-sm font-semibold text-graphite decoration-marker decoration-2 underline-offset-4 hover:text-ink hover:underline";
const CHOICE =
  "flex items-center gap-2 rounded-lg border-2 border-ink/15 bg-sheet px-3 py-2 text-sm font-medium transition " +
  "hover:border-ink hover:bg-lime";
const HAND = "font-hand text-xl leading-none text-graphite";

function Spinner() {
  return (
    <svg viewBox="0 0 24 24" width={18} height={18} className="motion-safe:animate-spin" aria-hidden>
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity={0.3} strokeWidth={3} />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" />
    </svg>
  );
}

function TopThree({ prediction, onPick }: { prediction: Prediction; onPick: (label: Label) => void }) {
  return (
    <ul className="flex flex-col gap-1.5" aria-label="Top three guesses">
      {prediction.top3.map((guess) => (
        <li key={guess.label}>
          <button type="button" className={`${CHOICE} w-full text-left`} onClick={() => onPick(guess.label)}>
            <LabelIcon label={guess.label} className={LABEL_COLOR[guess.label]} strokeWidth={2.2} />
            <span className="w-14 capitalize">{guess.label}</span>
            <span className="h-2 flex-1 overflow-hidden rounded-full border border-ink/20 bg-paper">
              <span className="block h-full rounded-full bg-marker" style={{ width: `${guess.score * 100}%` }} />
            </span>
            <span className="w-10 text-right text-xs tabular-nums text-graphite">{guess.score.toFixed(2)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function AllSix({ onPick }: { onPick: (label: Label) => void }) {
  return (
    <div>
      <p className={`${HAND} mb-2`}>something else?</p>
      <div className="grid grid-cols-3 gap-1.5">
        {LABELS.map((label) => (
          <button key={label} type="button" className={`${CHOICE} justify-center px-2 capitalize`} onClick={() => onPick(label)}>
            <LabelIcon label={label} className={LABEL_COLOR[label]} width={16} height={16} strokeWidth={2.2} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Answered({ prediction }: { prediction: Prediction }) {
  return (
    <p className="text-xs text-graphite">
      Answered by <span className="font-mono">{prediction.modelVersion}</span> in {prediction.latencyMs.toFixed(1)}{" "}
      ms on the server. Scores are not probabilities.
    </p>
  );
}

export function RecognizePanel({ flow, canRecognize, mocked, onRecognize, onConfirm, onPick, onRetry, onRevise }: Props) {
  const keepDrawing = (
    <button type="button" className={QUIET} onClick={onRevise}>
      Keep drawing
    </button>
  );

  return (
    <section
      className="flex w-full flex-col gap-4 rounded-[14px] border-2 border-ink bg-sheet p-5 shadow-ink-sm"
      aria-live="polite"
      aria-busy={flow.kind === "recognizing"}
    >
      {mocked ? (
        <p className="self-start rounded-full border-2 border-ink bg-pink px-2.5 py-0.5 text-xs font-bold text-white">
          Mock recognizer
        </p>
      ) : null}

      {flow.kind === "drawing" || flow.kind === "recognizing" ? (
        <>
          <div>
            <h2 className="font-display text-2xl font-extrabold tracking-tight">What did you draw?</h2>
            <p className="mt-1 text-sm text-graphite">Finish one drawing, then ask. It knows these six:</p>
          </div>
          <ul className="grid grid-cols-3 gap-1.5" aria-label="What it knows">
            {LABELS.map((label) => (
              <li
                key={label}
                className="flex items-center gap-1.5 rounded-lg border-2 border-ink/10 bg-paper px-2.5 py-2 text-sm font-medium capitalize"
              >
                <LabelIcon label={label} className={LABEL_COLOR[label]} width={16} height={16} strokeWidth={2.2} />
                {label}
              </li>
            ))}
          </ul>
          <button type="button" className={PRIMARY} disabled={!canRecognize} onClick={onRecognize}>
            {flow.kind === "recognizing" ? <Spinner /> : <SparkIcon />}
            {flow.kind === "recognizing" ? "Recognizing…" : "Recognize"}
          </button>
          <p className={HAND}>ctrl+z or ⌘z takes back a stroke</p>
        </>
      ) : null}

      {flow.kind === "suggested" ? (
        <>
          <div className="flex -rotate-1 items-center gap-4 rounded-xl border-2 border-ink bg-note p-4 shadow-ink-sm">
            <span className="grid size-14 shrink-0 place-items-center rounded-xl border-2 border-ink bg-sheet">
              <LabelIcon
                label={flow.prediction.label}
                className={LABEL_COLOR[flow.prediction.label]}
                width={32}
                height={32}
                strokeWidth={2}
              />
            </span>
            <div>
              <p className={HAND}>top score {flow.prediction.score.toFixed(2)}</p>
              <h2 className="font-display text-2xl font-extrabold tracking-tight">
                Looks like a{" "}
                <span key={flow.prediction.label} className="highlight" style={at(0.1)}>
                  {flow.prediction.label}
                </span>
                .
              </h2>
            </div>
          </div>
          <button type="button" className={PRIMARY} onClick={onConfirm}>
            Yes, it&apos;s a {flow.prediction.label}
          </button>
          <TopThree prediction={flow.prediction} onPick={onPick} />
          <AllSix onPick={onPick} />
          <Answered prediction={flow.prediction} />
          {keepDrawing}
        </>
      ) : null}

      {flow.kind === "choosing" ? (
        <>
          <div>
            <h2 className="font-display text-2xl font-extrabold tracking-tight">Not sure. Which one is it?</h2>
            <p className="mt-1 text-sm text-graphite">
              The top guesses are too close to call, so nothing is picked for you.
            </p>
          </div>
          <TopThree prediction={flow.prediction} onPick={onPick} />
          <AllSix onPick={onPick} />
          <Answered prediction={flow.prediction} />
          {keepDrawing}
        </>
      ) : null}

      {flow.kind === "failed" ? (
        <>
          <div>
            <h2 className="font-display text-2xl font-extrabold tracking-tight">That didn&apos;t work.</h2>
            <p className="mt-1 text-sm text-graphite">{flow.error.message}</p>
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
