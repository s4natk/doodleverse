"use client";

import { useEffect, useReducer, useState } from "react";

import { EMPTY_SKETCH, sketchReducer } from "../lib/sketch";
import { SketchPad, type Tool } from "./SketchPad";
import { THICKNESS, Toolbar } from "./Toolbar";

export function Studio() {
  const [sketch, dispatch] = useReducer(sketchReducer, EMPTY_SKETCH);
  const [tool, setTool] = useState<Tool>("pencil");
  const [width, setWidth] = useState<number>(THICKNESS[1].value);

  useEffect(() => {
    function undoOnShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === "z") {
        event.preventDefault();
        dispatch({ type: "undo" });
      }
    }
    window.addEventListener("keydown", undoOnShortcut);
    return () => window.removeEventListener("keydown", undoOnShortcut);
  }, []);

  return (
    <div className="flex flex-col gap-3">
      <Toolbar
        tool={tool}
        width={width}
        canUndo={sketch.history.length > 0}
        canClear={sketch.strokes.length > 0}
        onTool={setTool}
        onWidth={setWidth}
        onUndo={() => dispatch({ type: "undo" })}
        onClear={() => dispatch({ type: "clear" })}
      />
      <div className="aspect-[4/3] w-full">
        <SketchPad strokes={sketch.strokes} active={sketch.active} tool={tool} width={width} onAction={dispatch} />
      </div>
    </div>
  );
}
