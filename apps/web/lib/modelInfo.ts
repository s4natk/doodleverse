/** What `GET /model/info` says about the model answering right now. See docs/api.md. */
export type ModelInfo = {
  version: string;
  parameters: number | null;
  fileBytes: number | null;
  testCount: number | null;
  testAccuracy: number | null;
  testMacroF1: number | null;
  gateCoverage: number | null;
  gateAcceptedAccuracy: number | null;
};

function finite(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function parseModelInfo(body: unknown): ModelInfo | null {
  if (typeof body !== "object" || body === null) {
    return null;
  }
  const value = body as Record<string, unknown>;
  if (typeof value.model_version !== "string") {
    return null;
  }
  const test = (typeof value.test === "object" && value.test !== null ? value.test : {}) as Record<string, unknown>;
  return {
    version: value.model_version,
    parameters: finite(value.parameter_count),
    fileBytes: finite(value.file_bytes),
    testCount: finite(test.count),
    testAccuracy: finite(test.accuracy),
    testMacroF1: finite(test.macro_f1),
    gateCoverage: finite(test.gate_coverage),
    gateAcceptedAccuracy: finite(test.gate_accepted_accuracy),
  };
}

/** Null when the service is unreachable or answers with something else. The page works without it. */
export async function fetchModelInfo(
  baseUrl: string,
  signal?: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<ModelInfo | null> {
  try {
    const response = await fetchImpl(`${baseUrl.replace(/\/+$/, "")}/model/info`, { signal });
    return response.ok ? parseModelInfo(await response.json()) : null;
  } catch {
    return null;
  }
}
