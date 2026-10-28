import { MAX_POINTS, MAX_STROKES } from "./contract";
import { distanceToPolyline, type Point } from "./geometry";

export type Stroke = { id: number; points: Point[]; width: number };

export type SketchState = {
  strokes: Stroke[];
  /** The stroke under the pointer right now. It joins `strokes` on `end`. */
  active: Stroke | null;
  /** Earlier versions of `strokes`, newest last. */
  history: Stroke[][];
  /** `strokes` as they were when the eraser touched down, so one swipe is one undo step. */
  erasing: Stroke[] | null;
  nextId: number;
};

export type SketchAction =
  | { type: "begin"; point: Point; width: number }
  | { type: "extend"; points: Point[] }
  | { type: "end" }
  | { type: "cancel" }
  | { type: "eraseBegin" }
  | { type: "erase"; point: Point; radius: number }
  | { type: "eraseEnd" }
  | { type: "undo" }
  | { type: "clear" };

export const EMPTY_SKETCH: SketchState = { strokes: [], active: null, history: [], erasing: null, nextId: 1 };

// Points closer than this to the last one change nothing at 28×28 and only make the request bigger.
export const MIN_STEP = 1.5;

export function pointCount(strokes: readonly Stroke[]): number {
  return strokes.reduce((total, stroke) => total + stroke.points.length, 0);
}

function busy(state: SketchState): boolean {
  return state.active !== null || state.erasing !== null;
}

export function sketchReducer(state: SketchState, action: SketchAction): SketchState {
  switch (action.type) {
    case "begin": {
      if (busy(state) || state.strokes.length >= MAX_STROKES || pointCount(state.strokes) >= MAX_POINTS) {
        return state;
      }
      const active = { id: state.nextId, points: [action.point], width: action.width };
      return { ...state, active, nextId: state.nextId + 1 };
    }
    case "extend": {
      if (!state.active) {
        return state;
      }
      let room = MAX_POINTS - pointCount(state.strokes) - state.active.points.length;
      const points = [...state.active.points];
      for (const point of action.points) {
        const last = points[points.length - 1];
        if (room <= 0) {
          break;
        }
        if (Math.hypot(point[0] - last[0], point[1] - last[1]) >= MIN_STEP) {
          points.push(point);
          room -= 1;
        }
      }
      return points.length === state.active.points.length ? state : { ...state, active: { ...state.active, points } };
    }
    case "end":
      if (!state.active) {
        return state;
      }
      return { ...state, strokes: [...state.strokes, state.active], active: null, history: [...state.history, state.strokes] };
    case "cancel":
      return state.active ? { ...state, active: null } : state;
    case "eraseBegin":
      return busy(state) ? state : { ...state, erasing: state.strokes };
    case "erase": {
      if (!state.erasing) {
        return state;
      }
      const kept = state.strokes.filter(
        (stroke) => distanceToPolyline(action.point, stroke.points) > action.radius + stroke.width / 2,
      );
      return kept.length === state.strokes.length ? state : { ...state, strokes: kept };
    }
    case "eraseEnd": {
      if (!state.erasing) {
        return state;
      }
      const erasedSomething = state.strokes !== state.erasing;
      return { ...state, erasing: null, history: erasedSomething ? [...state.history, state.erasing] : state.history };
    }
    case "undo":
      if (busy(state) || state.history.length === 0) {
        return state;
      }
      return { ...state, strokes: state.history[state.history.length - 1], history: state.history.slice(0, -1) };
    case "clear":
      if (busy(state) || state.strokes.length === 0) {
        return state;
      }
      return { ...state, strokes: [], history: [...state.history, state.strokes] };
  }
}
