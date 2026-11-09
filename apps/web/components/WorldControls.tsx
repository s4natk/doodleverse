"use client";

import { PauseIcon, PlayIcon, ResetIcon, TrashIcon } from "./icons";
import { ACTION, GROUP, segment } from "./Toolbar";

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

export function WorldControls({ paused, speed, count, onPause, onSpeed, onClear, onReset }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="toolbar" aria-label="World controls">
      <button
        type="button"
        className={`${ACTION} ${paused ? "border-ink bg-lime text-ink" : ""}`}
        aria-pressed={paused}
        onClick={() => onPause(!paused)}
      >
        {paused ? <PlayIcon width={15} height={15} /> : <PauseIcon width={15} height={15} />}
        {paused ? "Resume" : "Pause"}
      </button>
      <div className={GROUP} role="group" aria-label="Speed">
        {SPEEDS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`${segment(speed === option.value)} px-2.5 py-1 tabular-nums`}
            aria-pressed={speed === option.value}
            onClick={() => onSpeed(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
      <span className="inline-flex items-center gap-2 px-1 text-sm font-medium text-graphite">
        <span
          className={`size-2.5 rounded-full border-2 border-ink ${count > 0 ? "bg-mint" : "bg-sheet"}`}
          aria-hidden
        />
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
