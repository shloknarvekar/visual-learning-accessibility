import type { Lesson } from "@visual-learning/contracts";
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
  /** Absent for a YouTube lesson, which has no uploaded file. */
  source_filename?: string;
  /** Absent for video and YouTube lessons, which have no pages. */
  page_count?: number;
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
  lesson: Lesson;
};

export const apiClient = {
  getHealth: () => request<HealthResponse>("/api/v1/health"),
  createLessonFromPdf: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<LessonRecord>("/api/v1/lessons/pdf", {
      method: "POST",
      body: form,
    });
  },
  createLessonFromVideo: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<LessonRecord>("/api/v1/lessons/video", {
      method: "POST",
      body: form,
    });
  },
  createLessonFromYoutube: (url: string) =>
    request<LessonRecord>("/api/v1/lessons/youtube", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    }),
  getLesson: (lessonId: string) =>
    request<LessonRecord>(`/api/v1/lessons/${encodeURIComponent(lessonId)}`),
};
