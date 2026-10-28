import { describe, expect, it, vi } from "vitest";

import { DEFAULT_API_URL, httpRecognizer, pickRecognizer, RecognizeError, toRequest } from "./inference";
import { mockPrediction, mockRecognizer } from "./mockRecognizer";
import type { Stroke } from "./sketch";

const REQUEST = { canvas: { width: 400, height: 300 }, strokes: [[[10, 10], [60, 40]] as [number, number][]] };

const ANSWER = {
  label: "sun",
  score: 0.98,
  top3: [
    { label: "sun", score: 0.98 },
    { label: "flower", score: 0.01 },
    { label: "cat", score: 0.005 },
  ],
  uncertain: false,
  model_version: "gap-1ce366c1a170",
  latency_ms: 2.9,
};

function respond(status: number, body: unknown): typeof fetch {
  return vi.fn(async () => new Response(typeof body === "string" ? body : JSON.stringify(body), { status }));
}

async function failure(promise: Promise<unknown>): Promise<RecognizeError> {
  const error = await promise.then(
    () => null,
    (reason: unknown) => reason,
  );
  expect(error).toBeInstanceOf(RecognizeError);
  return error as RecognizeError;
}

describe("request body", () => {
  it("rounds the canvas to whole pixels and sends [x, y] points", () => {
    const strokes: Stroke[] = [{ id: 1, points: [[1.5, 2.25], [9, 4]], width: 8 }];
    expect(toRequest(strokes, { width: 640.4, height: 479.6 })).toEqual({
      canvas: { width: 640, height: 480 },
      strokes: [[[1.5, 2.25], [9, 4]]],
    });
  });
});

describe("httpRecognizer", () => {
  it("posts the sketch to /predict and maps the answer", async () => {
    const fetchImpl = respond(200, ANSWER);
    const prediction = await httpRecognizer("http://api.test/", fetchImpl)(REQUEST);
    expect(fetchImpl).toHaveBeenCalledWith(
      "http://api.test/predict",
      expect.objectContaining({ method: "POST", body: JSON.stringify(REQUEST) }),
    );
    expect(prediction).toEqual({
      label: "sun",
      score: 0.98,
      top3: ANSWER.top3,
      uncertain: false,
      modelVersion: "gap-1ce366c1a170",
      latencyMs: 2.9,
    });
  });

  it("keeps the service's error code and message", async () => {
    const body = { error: { code: "too_many_strokes", message: "A sketch can contain at most 64 strokes." } };
    const error = await failure(httpRecognizer("http://api.test", respond(422, body))(REQUEST));
    expect([error.code, error.message, error.status]).toEqual(["too_many_strokes", body.error.message, 422]);
  });

  it("names the status when the error body is not the service's", async () => {
    const error = await failure(httpRecognizer("http://api.test", respond(502, "<html>bad gateway</html>"))(REQUEST));
    expect([error.code, error.status]).toEqual(["http_502", 502]);
  });

  it("refuses an answer with a label outside the six", async () => {
    const error = await failure(httpRecognizer("http://api.test", respond(200, { ...ANSWER, label: "dog" }))(REQUEST));
    expect(error.code).toBe("bad_response");
  });

  it("reports an unreachable service", async () => {
    const offline = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    const error = await failure(httpRecognizer("http://api.test", offline)(REQUEST));
    expect(error.code).toBe("unreachable");
  });

  it("gives up after the timeout", async () => {
    const hanging: typeof fetch = (_url, init) =>
      new Promise((_resolve, reject) => init?.signal?.addEventListener("abort", () => reject(new DOMException("", "AbortError"))));
    const error = await failure(httpRecognizer("http://api.test", hanging, 20)(REQUEST));
    expect(error.code).toBe("timeout");
  });

  it("passes a caller's cancel through as an abort, not an error to show", async () => {
    const hanging: typeof fetch = (_url, init) =>
      new Promise((_resolve, reject) => init?.signal?.addEventListener("abort", () => reject(new DOMException("", "AbortError"))));
    const controller = new AbortController();
    const pending = httpRecognizer("http://api.test", hanging)(REQUEST, controller.signal);
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  });
});

describe("pickRecognizer", () => {
  it("uses the mock only outside production, and only when asked", () => {
    expect(pickRecognizer({ nodeEnv: "development", mock: "1" }).mocked).toBe(true);
    expect(pickRecognizer({ nodeEnv: "test", mock: "1" }).recognize).toBe(mockRecognizer);
    expect(pickRecognizer({ nodeEnv: "production", mock: "1" }).mocked).toBe(false);
    expect(pickRecognizer({ nodeEnv: "development" }).mocked).toBe(false);
  });

  it("falls back to the local API address", async () => {
    const fetchImpl = respond(200, ANSWER);
    vi.stubGlobal("fetch", fetchImpl);
    await pickRecognizer({ nodeEnv: "production" }).recognize(REQUEST);
    expect(fetchImpl).toHaveBeenCalledWith(`${DEFAULT_API_URL}/predict`, expect.anything());
    vi.unstubAllGlobals();
  });
});

describe("mock recognizer", () => {
  it("answers in the service's shape and is sometimes unsure", () => {
    const one = mockPrediction(REQUEST);
    expect(one.top3).toHaveLength(3);
    expect(one.label).toBe(one.top3[0].label);
    expect(mockPrediction(REQUEST)).toEqual(one);
    const three = mockPrediction({ ...REQUEST, strokes: [[[1, 1]], [[2, 2]], [[3, 3]]] });
    expect(three.uncertain).toBe(true);
  });
});
