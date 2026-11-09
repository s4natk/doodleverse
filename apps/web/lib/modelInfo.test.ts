import { describe, expect, it, vi } from "vitest";

import { fetchModelInfo, parseModelInfo } from "./modelInfo";

const INFO = {
  model_version: "gap-1ce366c1a170",
  parameter_count: 94118,
  file_bytes: 433944,
  test: { count: 3600, accuracy: 0.9503, macro_f1: 0.9502, gate_coverage: 0.8683, gate_accepted_accuracy: 0.9914 },
};

describe("model info", () => {
  it("keeps the numbers the page shows", () => {
    expect(parseModelInfo(INFO)).toEqual({
      version: "gap-1ce366c1a170",
      parameters: 94118,
      fileBytes: 433944,
      testCount: 3600,
      testAccuracy: 0.9503,
      testMacroF1: 0.9502,
      gateCoverage: 0.8683,
      gateAcceptedAccuracy: 0.9914,
    });
  });

  it("leaves test numbers empty before the test split is scored", () => {
    expect(parseModelInfo({ ...INFO, test: null })).toMatchObject({ testAccuracy: null, gateCoverage: null });
  });

  it("refuses an answer without a model version", () => {
    expect(parseModelInfo({ ...INFO, model_version: 3 })).toBeNull();
    expect(parseModelInfo("gap")).toBeNull();
  });

  it("is null when the service cannot be reached or says no", async () => {
    const offline = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    expect(await fetchModelInfo("http://api.test", undefined, offline)).toBeNull();
    const refused = vi.fn(async () => new Response("{}", { status: 503 }));
    expect(await fetchModelInfo("http://api.test", undefined, refused)).toBeNull();
    const ok = vi.fn(async () => new Response(JSON.stringify(INFO), { status: 200 }));
    expect((await fetchModelInfo("http://api.test/", undefined, ok))?.version).toBe("gap-1ce366c1a170");
    expect(ok).toHaveBeenCalledWith("http://api.test/model/info", expect.anything());
  });
});
