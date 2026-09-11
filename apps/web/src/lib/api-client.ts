import { config } from "./config";

export type HealthResponse = {
  status: "ok";
  service: string;
  version: string;
  /** "mock" when the API has no AI key configured and serves example lessons. */
  ai_mode: "gemini" | "mock";
};

/** Envelope the API returns for every non-2xx response. */
type ApiErrorBody = {
  error: { code: string; message: string; details?: unknown };
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(
      response.status,
      body?.error.code ?? "unknown_error",
      body?.error.message ?? `Request failed with status ${response.status}`,
    );
  }

  return (await response.json()) as T;
}

/** Typed wrapper around the FastAPI service. Add lesson endpoints here as the API exposes them. */
export const apiClient = {
  getHealth: () => request<HealthResponse>("/api/v1/health"),
};
