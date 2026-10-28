"use client";

import type { Tool } from "./SketchPad";

export const THICKNESS = [
  { label: "Thin", value: 4 },
  { label: "Medium", value: 8 },
  { label: "Thick", value: 14 },
] as const;

type Props = {
  tool: Tool;
  width: number;
  canUndo: boolean;
  canClear: boolean;
  disabled?: boolean;
  onTool: (tool: Tool) => void;
  onWidth: (width: number) => void;
  onUndo: () => void;
  onClear: () => void;
};

const BUTTON = "rounded-full px-3 py-1.5 text-sm transition disabled:cursor-not-allowed disabled:opacity-40";

function toggleClass(on: boolean): string {
  return `${BUTTON} ${on ? "bg-[#2c2733] text-[#f3e6d4]" : "bg-white/70 text-[#2c2733] hover:bg-white"}`;
}

export function Toolbar({ tool, width, canUndo, canClear, disabled = false, onTool, onWidth, onUndo, onClear }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="toolbar" aria-label="Drawing tools">
      <div className="flex gap-1 rounded-full bg-black/5 p-1">
        {(["pencil", "eraser"] as const).map((option) => (
          <button
            key={option}
            type="button"
            className={toggleClass(tool === option)}
            aria-pressed={tool === option}
            disabled={disabled}
            onClick={() => onTool(option)}
          >
            {option === "pencil" ? "Pencil" : "Eraser"}
          </button>
        ))}
      </div>
      <div className="flex gap-1 rounded-full bg-black/5 p-1" role="group" aria-label="Line thickness">
        {THICKNESS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={toggleClass(width === option.value)}
            aria-pressed={width === option.value}
            disabled={disabled || tool !== "pencil"}
            onClick={() => onWidth(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
      <div className="ml-auto flex gap-1">
        <button
          type="button"
          className={`${BUTTON} bg-white/70 hover:bg-white`}
          disabled={disabled || !canUndo}
          title="Undo (Ctrl+Z)"
          onClick={onUndo}
        >
          Undo
        </button>
        <button
          type="button"
          className={`${BUTTON} bg-white/70 hover:bg-white`}
          disabled={disabled || !canClear}
          onClick={onClear}
        >
          Clear
        </button>
      </div>
    </div>
  );
}
