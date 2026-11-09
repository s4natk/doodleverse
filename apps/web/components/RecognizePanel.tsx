"use client";

import { LABELS, type Label } from "../lib/contract";
import type { Prediction } from "../lib/inference";
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

const PRIMARY =
  "flex w-full items-center justify-center gap-2 rounded-full bg-gradient-warm px-5 py-3 font-display text-base " +
  "font-semibold text-white shadow-[0_12px_26px_-12px_rgba(236,106,76,0.9)] transition hover:brightness-105 " +
  "active:translate-y-px disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none";
const QUIET = "self-start rounded-full px-3 py-1.5 text-sm font-medium text-muted transition hover:bg-black/5 hover:text-ink";
const CHOICE =
  "flex items-center gap-2 rounded-xl border border-line bg-white px-3 py-2 text-sm transition " +
  "hover:border-coral/40 hover:bg-[#fff5f1]";
const EYEBROW = "text-xs font-medium uppercase tracking-[0.14em] text-muted";

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
            <LabelIcon label={guess.label} className={LABEL_COLOR[guess.label]} />
            <span className="w-14 capitalize">{guess.label}</span>
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-black/[0.06]">
              <span className="block h-full rounded-full bg-gradient-warm" style={{ width: `${guess.score * 100}%` }} />
            </span>
            <span className="w-10 text-right text-xs tabular-nums text-muted">{guess.score.toFixed(2)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function AllSix({ onPick }: { onPick: (label: Label) => void }) {
  return (
    <div>
      <p className={`${EYEBROW} mb-2`}>Something else?</p>
      <div className="grid grid-cols-3 gap-1.5">
        {LABELS.map((label) => (
          <button
            key={label}
            type="button"
            className={`${CHOICE} justify-center px-2 capitalize`}
            onClick={() => onPick(label)}
          >
            <LabelIcon label={label} className={LABEL_COLOR[label]} width={16} height={16} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Answered({ prediction }: { prediction: Prediction }) {
  return (
    <p className="text-xs text-muted">
      Answered by <span className="font-mono">{prediction.modelVersion}</span> in{" "}
      {prediction.latencyMs.toFixed(1)} ms on the server. Scores are not probabilities.
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
      className="flex w-full flex-col gap-4 rounded-2xl border border-line bg-white/85 p-5 shadow-[0_1px_0_rgba(0,0,0,0.03)]"
      aria-live="polite"
      aria-busy={flow.kind === "recognizing"}
    >
      {mocked ? (
        <p className="self-start rounded-full bg-coral/10 px-2.5 py-0.5 text-xs font-medium text-coral">
          Mock recognizer
        </p>
      ) : null}

      {flow.kind === "drawing" || flow.kind === "recognizing" ? (
        <>
          <div>
            <h2 className="font-display text-2xl font-semibold tracking-tight">What did you draw?</h2>
            <p className="mt-1 text-sm text-muted">Finish one drawing, then ask. It knows these six:</p>
          </div>
          <ul className="grid grid-cols-3 gap-1.5" aria-label="What it knows">
            {LABELS.map((label) => (
              <li
                key={label}
                className="flex items-center gap-1.5 rounded-xl bg-black/[0.035] px-2.5 py-2 text-sm capitalize text-ink/80"
              >
                <LabelIcon label={label} className={LABEL_COLOR[label]} width={16} height={16} />
                {label}
              </li>
            ))}
          </ul>
          <button type="button" className={PRIMARY} disabled={!canRecognize} onClick={onRecognize}>
            {flow.kind === "recognizing" ? <Spinner /> : <SparkIcon />}
            {flow.kind === "recognizing" ? "Recognizing…" : "Recognize"}
          </button>
          <p className="text-xs text-muted">Ctrl+Z or ⌘Z undoes the last stroke.</p>
        </>
      ) : null}

      {flow.kind === "suggested" ? (
        <>
          <div className="flex items-center gap-4 rounded-2xl bg-gradient-to-br from-[#fff0ea] to-[#fff6e6] p-4">
            <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-white shadow-sm">
              <LabelIcon
                label={flow.prediction.label}
                className={LABEL_COLOR[flow.prediction.label]}
                width={32}
                height={32}
                strokeWidth={1.6}
              />
            </span>
            <div>
              <p className={EYEBROW}>Top score {flow.prediction.score.toFixed(2)}</p>
              <h2 className="font-display text-2xl font-semibold tracking-tight">
                Looks like a {flow.prediction.label}.
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
            <h2 className="font-display text-2xl font-semibold tracking-tight">Not sure. Which one is it?</h2>
            <p className="mt-1 text-sm text-muted">
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
            <h2 className="font-display text-2xl font-semibold tracking-tight">That didn&apos;t work.</h2>
            <p className="mt-1 text-sm text-muted">{flow.error.message}</p>
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
