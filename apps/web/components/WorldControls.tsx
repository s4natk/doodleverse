"use client";

import { PauseIcon, PlayIcon, ResetIcon, TrashIcon } from "./icons";

export const SPEEDS = [
  { label: "0.5×", value: 0.5 },
  { label: "1×", value: 1 },
  { label: "2×", value: 2 },
] as const;

type Props = {
  paused: boolean;
  speed: number;
  count: number;
  onPause: (paused: boolean) => void;
  onSpeed: (speed: number) => void;
  onClear: () => void;
  onReset: () => void;
};

const ACTION =
  "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium text-muted transition hover:bg-black/5 " +
  "hover:text-ink disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-transparent";

function segment(on: boolean): string {
  return (
    "rounded-full px-2.5 py-1 text-sm font-medium tabular-nums transition " +
    (on ? "bg-white text-ink shadow-sm ring-1 ring-black/5" : "text-muted hover:text-ink")
  );
}

export function WorldControls({ paused, speed, count, onPause, onSpeed, onClear, onReset }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="toolbar" aria-label="World controls">
      <button
        type="button"
        className={`${ACTION} ${paused ? "bg-ink text-white hover:bg-ink hover:text-white" : ""}`}
        aria-pressed={paused}
        onClick={() => onPause(!paused)}
      >
        {paused ? <PlayIcon width={15} height={15} /> : <PauseIcon width={15} height={15} />}
        {paused ? "Resume" : "Pause"}
      </button>
      <div className="inline-flex gap-0.5 rounded-full bg-black/[0.045] p-1" role="group" aria-label="Speed">
        {SPEEDS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={segment(speed === option.value)}
            aria-pressed={speed === option.value}
            onClick={() => onSpeed(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
      <span className="inline-flex items-center gap-2 rounded-full px-2 text-sm text-muted">
        <span className={`size-2 rounded-full ${count > 0 ? "bg-leaf" : "bg-black/20"}`} aria-hidden />
        {count === 1 ? "1 thing" : `${count} things`} in the world
      </span>
      <div className="ml-auto flex gap-1">
        <button type="button" className={ACTION} disabled={count === 0} onClick={onClear}>
          <TrashIcon width={15} height={15} />
          Clear world
        </button>
        <button type="button" className={ACTION} onClick={onReset}>
          <ResetIcon width={15} height={15} />
          Reset
        </button>
      </div>
    </div>
  );
}
