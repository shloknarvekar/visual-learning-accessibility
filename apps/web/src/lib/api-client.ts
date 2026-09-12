import { config } from "./config";

export type HealthResponse = {
  status: "ok";
  service: string;
  version: string;
  ai_mode: "gemini" | "openrouter" | "groq" | "mock";
};

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

export type GenerationStatus = "live" | "fallback" | "cached" | "demo";
export type LessonMetadata = {
  provider: "gemini" | "openrouter" | "groq" | "cache" | "demo";
  generation_status: GenerationStatus;
  is_mock: boolean;
  notice?: string;
  model?: string;
  source_filename: string;
  page_count: number;
  chunk_count: number;
  character_count: number;
  ai_request_count: number;
  warnings: string[];
  timings: {
    extraction_ms: number;
    chunking_ms: number;
    generation_ms: number;
    validation_ms: number;
    total_ms: number;
  };
  created_at: string;
};

export type LessonRecord = {
  lesson_id: string;
  metadata: LessonMetadata;
  lesson: import("@visual-learning/contracts").Lesson;
};

export const apiClient = {
  getHealth: () => request<HealthResponse>("/api/v1/health"),
  createPdfLesson: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<LessonRecord>("/api/v1/lessons/pdf", {
      method: "POST",
      body: form,
    });
  },
  getLesson: (lessonId: string) => request<LessonRecord>(`/api/v1/lessons/${encodeURIComponent(lessonId)}`),
};
