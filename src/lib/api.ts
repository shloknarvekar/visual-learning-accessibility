export type LessonMode = 'live' | 'fallback' | 'demo';

export type LessonApiResult = {
  lesson?: unknown;
  mode?: LessonMode;
  message?: string;
  requestId?: string;
};

const endpoint = process.env.NEXT_PUBLIC_LESSON_API_URL?.trim();

export function isLiveApiConfigured() {
  return Boolean(endpoint);
}

export async function createLessonFromFrontend(input: {
  source: 'youtube' | 'pdf';
  url?: string;
  file?: File | null;
}): Promise<LessonApiResult> {
  if (!endpoint) return { mode: 'demo' };

  const form = new FormData();
  form.append('source', input.source);
  if (input.url) form.append('url', input.url);
  if (input.file) form.append('file', input.file);

  const response = await fetch(endpoint, {
    method: 'POST',
    body: form,
    headers: { Accept: 'application/json' },
  });

  const payload = (await response.json().catch(() => ({}))) as LessonApiResult;
  if (!response.ok) {
    throw new Error(payload.message || `Lesson service returned ${response.status}.`);
  }
  return payload;
}
