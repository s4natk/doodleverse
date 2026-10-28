import { LABELS } from "./contract";
import type { Prediction, Recognizer, SketchRequest } from "./inference";

// Stands in for the API while working on the page without Python running. Every third
// sketch comes back uncertain so the pick-one path gets exercised too.
export function mockPrediction(request: SketchRequest): Prediction {
  const points = request.strokes.reduce((total, stroke) => total + stroke.length, 0);
  const first = (request.strokes.length + points) % LABELS.length;
  const uncertain = request.strokes.length % 3 === 0;
  const scores = uncertain ? [0.46, 0.38, 0.09] : [0.91, 0.05, 0.02];
  const top3 = scores.map((score, rank) => ({ label: LABELS[(first + rank) % LABELS.length], score }));
  return { label: top3[0].label, score: top3[0].score, top3, uncertain, modelVersion: "mock", latencyMs: 0 };
}

function wait(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(signal.reason ?? new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

export const mockRecognizer: Recognizer = async (request, signal) => {
  await wait(350, signal);
  return mockPrediction(request);
};
