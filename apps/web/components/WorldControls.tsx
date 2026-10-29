"use client";

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

const BUTTON = "rounded-full px-3 py-1.5 text-sm transition disabled:cursor-not-allowed disabled:opacity-40";

function toggleClass(on: boolean): string {
  return `${BUTTON} ${on ? "bg-[#2c2733] text-[#f3e6d4]" : "bg-white/70 text-[#2c2733] hover:bg-white"}`;
}

export function WorldControls({ paused, speed, count, onPause, onSpeed, onClear, onReset }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="toolbar" aria-label="World controls">
      <button type="button" className={toggleClass(paused)} aria-pressed={paused} onClick={() => onPause(!paused)}>
        {paused ? "Resume" : "Pause"}
      </button>
      <div className="flex gap-1 rounded-full bg-black/5 p-1" role="group" aria-label="Speed">
        {SPEEDS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={toggleClass(speed === option.value)}
            aria-pressed={speed === option.value}
            onClick={() => onSpeed(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
      <span className="text-sm text-black/50">{count === 1 ? "1 thing" : `${count} things`} in the world</span>
      <div className="ml-auto flex gap-1">
        <button type="button" className={`${BUTTON} bg-white/70 hover:bg-white`} disabled={count === 0} onClick={onClear}>
          Clear world
        </button>
        <button type="button" className={`${BUTTON} bg-white/70 hover:bg-white`} onClick={onReset}>
          Reset
        </button>
      </div>
    </div>
  );
}
