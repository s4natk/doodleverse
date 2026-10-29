"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { pickRecognizer, RecognizeError, type CanvasSize } from "../lib/inference";
import { readStep, saveStep } from "../lib/onboarding";
import type { SketchAction } from "../lib/sketch";
import { canRecognize, INITIAL_STUDIO, studioReducer } from "../lib/studio";
import { FirstUsePrompt } from "./FirstUsePrompt";
import { RecognizePanel } from "./RecognizePanel";
import { SketchPad, type Tool } from "./SketchPad";
import { THICKNESS, Toolbar } from "./Toolbar";
import { World, type WorldHandle } from "./World";
import { WorldControls } from "./WorldControls";

export function Studio() {
  const [state, dispatch] = useReducer(studioReducer, INITIAL_STUDIO);
  const [tool, setTool] = useState<Tool>("pencil");
  const [width, setWidth] = useState<number>(THICKNESS[1].value);
  const [canvasSize, setCanvasSize] = useState<CanvasSize | null>(null);
  const [{ recognize, mocked }] = useState(() => pickRecognizer());
  const worldRef = useRef<WorldHandle>(null);
  const [paused, setPaused] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [count, setCount] = useState(0);
  const { sketch, flow } = state;
  const locked = flow.kind === "recognizing";

  const onSketch = useCallback((action: SketchAction) => dispatch({ type: "sketch", action }), []);
  const onSpawned = useCallback((id: number) => dispatch({ type: "spawned", id }), []);

  useEffect(() => {
    dispatch({ type: "firstUse", step: readStep(window.localStorage) });
  }, []);

  useEffect(() => {
    if (state.firstUse === "done") {
      saveStep(window.localStorage, "done");
    }
  }, [state.firstUse]);

  useEffect(() => {
    function undoOnShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === "z") {
        event.preventDefault();
        dispatch({ type: "sketch", action: { type: "undo" } });
      }
    }
    window.addEventListener("keydown", undoOnShortcut);
    return () => window.removeEventListener("keydown", undoOnShortcut);
  }, []);

  useEffect(() => {
    if (flow.kind !== "recognizing") {
      return;
    }
    const { requestId, request } = flow;
    const controller = new AbortController();
    recognize(request, controller.signal).then(
      (prediction) => dispatch({ type: "resolved", requestId, prediction }),
      (error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const failure =
          error instanceof RecognizeError
            ? { code: error.code, message: error.message }
            : { code: "unknown", message: "Something went wrong. Try again." };
        dispatch({ type: "rejected", requestId, error: failure });
      },
    );
    return () => controller.abort();
  }, [flow, recognize]);

  return (
    <div className="grid gap-6 md:grid-cols-[minmax(0,1fr)_300px]">
      <div className="flex flex-col gap-3">
        <Toolbar
          tool={tool}
          width={width}
          canUndo={sketch.history.length > 0}
          canClear={sketch.strokes.length > 0}
          disabled={locked}
          onTool={setTool}
          onWidth={setWidth}
          onUndo={() => onSketch({ type: "undo" })}
          onClear={() => onSketch({ type: "clear" })}
        />
        {/* The sketch layer sits exactly over the world, so a confirmed drawing settles from where it was drawn. */}
        <div className="relative aspect-[4/3] w-full">
          <div className="absolute inset-0">
            <World
              ref={worldRef}
              placements={state.placed}
              paused={paused}
              speed={speed}
              onSpawned={onSpawned}
              onCountChange={setCount}
            />
          </div>
          <div className="absolute inset-0">
            <SketchPad
              strokes={sketch.strokes}
              active={sketch.active}
              tool={tool}
              width={width}
              disabled={locked}
              onAction={onSketch}
              onResize={setCanvasSize}
            />
          </div>
          <FirstUsePrompt step={state.firstUse} />
        </div>
        <WorldControls
          paused={paused}
          speed={speed}
          count={count}
          onPause={setPaused}
          onSpeed={setSpeed}
          onClear={() => worldRef.current?.clear()}
          onReset={() => {
            worldRef.current?.reset();
            setPaused(false);
            setSpeed(1);
            saveStep(window.localStorage, "sun");
            dispatch({ type: "firstUse", step: "sun" });
          }}
        />
      </div>
      <RecognizePanel
        flow={flow}
        canRecognize={canvasSize !== null && canRecognize(state)}
        mocked={mocked}
        onRecognize={() => canvasSize && dispatch({ type: "recognize", canvas: canvasSize })}
        onConfirm={() => dispatch({ type: "confirm" })}
        onPick={(label) => dispatch({ type: "pick", label })}
        onRetry={() => dispatch({ type: "retry" })}
        onRevise={() => dispatch({ type: "revise" })}
      />
    </div>
  );
}
