"use client";

import { EraserIcon, PencilIcon, TrashIcon, UndoIcon } from "./icons";
import type { Tool } from "./SketchPad";

export const THICKNESS = [
  { label: "Thin", value: 4, dot: "size-1.5" },
  { label: "Medium", value: 8, dot: "size-2.5" },
  { label: "Thick", value: 14, dot: "size-3.5" },
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

export const GROUP = "inline-flex items-center gap-0.5 rounded-full border-2 border-ink bg-sheet p-0.5";
export const ACTION =
  "inline-flex items-center gap-1.5 rounded-lg border-2 border-transparent px-2.5 py-1 text-sm font-semibold " +
  "text-graphite transition hover:border-ink hover:bg-lime hover:text-ink disabled:cursor-not-allowed " +
  "disabled:opacity-35 disabled:hover:border-transparent disabled:hover:bg-transparent";

export function segment(on: boolean): string {
  return (
    "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition " +
    "disabled:cursor-not-allowed disabled:opacity-35 " +
    (on ? "bg-lime text-ink" : "text-graphite hover:text-ink")
  );
}

export function Toolbar({ tool, width, canUndo, canClear, disabled = false, onTool, onWidth, onUndo, onClear }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="toolbar" aria-label="Drawing tools">
      <div className={GROUP}>
        {(["pencil", "eraser"] as const).map((option) => (
          <button
            key={option}
            type="button"
            className={segment(tool === option)}
            aria-pressed={tool === option}
            disabled={disabled}
            onClick={() => onTool(option)}
          >
            {option === "pencil" ? <PencilIcon width={16} height={16} /> : <EraserIcon width={16} height={16} />}
            {option === "pencil" ? "Pencil" : "Eraser"}
          </button>
        ))}
      </div>
      <div className={GROUP} role="group" aria-label="Line thickness">
        {THICKNESS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`${segment(width === option.value)} h-8 w-9 justify-center px-0`}
            aria-pressed={width === option.value}
            aria-label={option.label}
            title={option.label}
            disabled={disabled || tool !== "pencil"}
            onClick={() => onWidth(option.value)}
          >
            <span className={`${option.dot} rounded-full bg-current`} />
          </button>
        ))}
      </div>
      <div className="ml-auto flex gap-1">
        <button
          type="button"
          className={ACTION}
          disabled={disabled || !canUndo}
          aria-label="Undo"
          title="Undo (Ctrl+Z)"
          onClick={onUndo}
        >
          <UndoIcon width={16} height={16} />
          <span className="hidden sm:inline">Undo</span>
        </button>
        <button
          type="button"
          className={ACTION}
          disabled={disabled || !canClear}
          aria-label="Clear"
          title="Clear the drawing"
          onClick={onClear}
        >
          <TrashIcon width={16} height={16} />
          <span className="hidden sm:inline">Clear</span>
        </button>
      </div>
    </div>
  );
}
