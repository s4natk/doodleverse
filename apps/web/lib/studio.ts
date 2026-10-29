import type { Label } from "./contract";
import { boundsOf, type Bounds } from "./geometry";
import { toRequest, type CanvasSize, type Prediction, type SketchRequest } from "./inference";
import { EMPTY_SKETCH, sketchReducer, type SketchAction, type SketchState, type Stroke } from "./sketch";

export type Failure = { code: string; message: string };

export type Flow =
  | { kind: "drawing" }
  | { kind: "recognizing"; requestId: number; request: SketchRequest }
  /** Confident: one tap confirms the top guess. */
  | { kind: "suggested"; prediction: Prediction }
  /** Uncertain: nothing is chosen until the person picks. */
  | { kind: "choosing"; prediction: Prediction }
  | { kind: "failed"; request: SketchRequest; error: Failure };

export type Placement = {
  id: number;
  label: Label;
  /** True when the person chose the label instead of accepting the suggestion. */
  picked: boolean;
  strokes: Stroke[];
  bounds: Bounds;
  canvas: CanvasSize;
};

export type StudioState = {
  sketch: SketchState;
  flow: Flow;
  /** Confirmed drawings the world has not spawned yet. */
  placed: Placement[];
  /** The canvas size the last request was made with. */
  canvas: CanvasSize | null;
  nextRequest: number;
  nextPlacement: number;
};

export type StudioEvent =
  | { type: "sketch"; action: SketchAction }
  | { type: "recognize"; canvas: CanvasSize }
  | { type: "resolved"; requestId: number; prediction: Prediction }
  | { type: "rejected"; requestId: number; error: Failure }
  | { type: "confirm" }
  | { type: "pick"; label: Label }
  | { type: "retry" }
  | { type: "revise" }
  | { type: "spawned"; id: number };

export const INITIAL_STUDIO: StudioState = {
  sketch: EMPTY_SKETCH,
  flow: { kind: "drawing" },
  placed: [],
  canvas: null,
  nextRequest: 1,
  nextPlacement: 1,
};

const DRAWING: Flow = { kind: "drawing" };

export function canRecognize(state: StudioState): boolean {
  const { sketch } = state;
  return state.flow.kind === "drawing" && sketch.strokes.length > 0 && !sketch.active && !sketch.erasing;
}

function recognizing(state: StudioState, request: SketchRequest): StudioState {
  return {
    ...state,
    flow: { kind: "recognizing", requestId: state.nextRequest, request },
    nextRequest: state.nextRequest + 1,
  };
}

function place(state: StudioState, label: Label, picked: boolean): StudioState {
  const strokes = state.sketch.strokes;
  const bounds = boundsOf(strokes.map((stroke) => stroke.points));
  if (!bounds || !state.canvas) {
    return state;
  }
  const placement = { id: state.nextPlacement, label, picked, strokes, bounds, canvas: state.canvas };
  return {
    ...state,
    sketch: EMPTY_SKETCH,
    flow: DRAWING,
    placed: [...state.placed, placement],
    nextPlacement: state.nextPlacement + 1,
  };
}

export function studioReducer(state: StudioState, event: StudioEvent): StudioState {
  const { flow } = state;
  switch (event.type) {
    case "sketch": {
      if (flow.kind === "recognizing") {
        return state;
      }
      const sketch = sketchReducer(state.sketch, event.action);
      if (sketch === state.sketch) {
        return state;
      }
      return { ...state, sketch, flow: flow.kind === "drawing" ? flow : DRAWING };
    }
    case "recognize":
      if (!canRecognize(state)) {
        return state;
      }
      return recognizing({ ...state, canvas: event.canvas }, toRequest(state.sketch.strokes, event.canvas));
    case "resolved":
      if (flow.kind !== "recognizing" || flow.requestId !== event.requestId) {
        return state;
      }
      return {
        ...state,
        flow: event.prediction.uncertain
          ? { kind: "choosing", prediction: event.prediction }
          : { kind: "suggested", prediction: event.prediction },
      };
    case "rejected":
      if (flow.kind !== "recognizing" || flow.requestId !== event.requestId) {
        return state;
      }
      return { ...state, flow: { kind: "failed", request: flow.request, error: event.error } };
    case "confirm":
      return flow.kind === "suggested" ? place(state, flow.prediction.label, false) : state;
    case "pick":
      if (flow.kind !== "suggested" && flow.kind !== "choosing") {
        return state;
      }
      return place(state, event.label, flow.kind === "choosing" || event.label !== flow.prediction.label);
    case "retry":
      return flow.kind === "failed" ? recognizing(state, flow.request) : state;
    case "revise":
      return flow.kind === "suggested" || flow.kind === "choosing" || flow.kind === "failed"
        ? { ...state, flow: DRAWING }
        : state;
    case "spawned": {
      const placed = state.placed.filter((placement) => placement.id > event.id);
      return placed.length === state.placed.length ? state : { ...state, placed };
    }
  }
}
