import { isLabel, type Label } from "./contract";
import { mockRecognizer } from "./mockRecognizer";
import type { Stroke } from "./sketch";

export type Guess = { label: Label; score: number };

export type Prediction = {
  label: Label;
  score: number;
  top3: Guess[];
  uncertain: boolean;
  modelVersion: string;
  latencyMs: number;
};

export type CanvasSize = { width: number; height: number };

/** The body `POST /predict` takes. See docs/api.md. */
export type SketchRequest = {
  canvas: CanvasSize;
  strokes: [number, number][][];
};

export type Recognizer = (request: SketchRequest, signal?: AbortSignal) => Promise<Prediction>;

export class RecognizeError extends Error {
  readonly code: string;
  readonly status?: number;

  constructor(code: string, message: string, status?: number) {
    super(message);
    this.name = "RecognizeError";
    this.code = code;
    this.status = status;
  }
}

export const DEFAULT_API_URL = "http://127.0.0.1:8000";
export const TIMEOUT_MS = 8000;

export function toRequest(strokes: readonly Stroke[], canvas: CanvasSize): SketchRequest {
  return {
    canvas: { width: Math.max(1, Math.round(canvas.width)), height: Math.max(1, Math.round(canvas.height)) },
    strokes: strokes.map((stroke) => stroke.points.map(([x, y]) => [x, y])),
  };
}

function badResponse(): RecognizeError {
  return new RecognizeError("bad_response", "The recognizer sent an answer this page does not understand.");
}

export function parsePrediction(body: unknown): Prediction {
  if (typeof body !== "object" || body === null) {
    throw badResponse();
  }
  const value = body as Record<string, unknown>;
  if (
    !isLabel(value.label) ||
    typeof value.score !== "number" ||
    typeof value.uncertain !== "boolean" ||
    typeof value.model_version !== "string" ||
    !Array.isArray(value.top3) ||
    value.top3.length === 0
  ) {
    throw badResponse();
  }
  const top3 = value.top3.map((guess: unknown): Guess => {
    const item = guess as Record<string, unknown> | null;
    if (!item || !isLabel(item.label) || typeof item.score !== "number") {
      throw badResponse();
    }
    return { label: item.label, score: item.score };
  });
  return {
    label: value.label,
    score: value.score,
    top3,
    uncertain: value.uncertain,
    modelVersion: value.model_version,
    latencyMs: typeof value.latency_ms === "number" ? value.latency_ms : 0,
  };
}

export function httpRecognizer(baseUrl: string, fetchImpl: typeof fetch = fetch, timeoutMs = TIMEOUT_MS): Recognizer {
  const endpoint = `${baseUrl.replace(/\/+$/, "")}/predict`;
  return async (request, signal) => {
    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
    const forwardAbort = () => controller.abort(signal?.reason);
    signal?.addEventListener("abort", forwardAbort, { once: true });
    try {
      const response = await fetchImpl(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: controller.signal,
      });
      const body: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const error = (body as { error?: { code?: unknown; message?: unknown } } | null)?.error;
        throw new RecognizeError(
          typeof error?.code === "string" ? error.code : `http_${response.status}`,
          typeof error?.message === "string" ? error.message : `The recognizer answered ${response.status}.`,
          response.status,
        );
      }
      return parsePrediction(body);
    } catch (error) {
      if (error instanceof RecognizeError || signal?.aborted) {
        throw error;
      }
      if (timedOut) {
        throw new RecognizeError("timeout", "Recognition took too long. Try again.");
      }
      throw new RecognizeError("unreachable", "Could not reach the recognizer. Check that the API is running.");
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", forwardAbort);
    }
  };
}

type RecognizerEnv = { nodeEnv?: string; mock?: string; apiUrl?: string };

/** The real API, or the mock when NEXT_PUBLIC_MOCK_INFERENCE=1 outside a production build. */
export function pickRecognizer(
  env: RecognizerEnv = {
    nodeEnv: process.env.NODE_ENV,
    mock: process.env.NEXT_PUBLIC_MOCK_INFERENCE,
    apiUrl: process.env.NEXT_PUBLIC_API_URL,
  },
): { recognize: Recognizer; mocked: boolean } {
  if (env.nodeEnv !== "production" && env.mock === "1") {
    return { recognize: mockRecognizer, mocked: true };
  }
  return { recognize: httpRecognizer(env.apiUrl || DEFAULT_API_URL), mocked: false };
}
