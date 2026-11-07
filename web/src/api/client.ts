import type {
  ApiErrorPayload,
  Book,
  BookDetail,
  BookList,
  ConversionInput,
  Job,
  Preview,
  Settings,
  Voice,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";
const API_TOKEN = import.meta.env.VITE_API_TOKEN as string | undefined;

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: unknown;

  constructor(message: string, code = "api_error", status = 0, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export function authHeaders(): Record<string, string> {
  return API_TOKEN ? { "X-Vibebook-Token": API_TOKEN } : {};
}

function headersFor(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers);
  if (API_TOKEN) {
    headers.set("X-Vibebook-Token", API_TOKEN);
  }
  return headers;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = headersFor(init);
  const body = init.body;
  if (body && typeof body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    let payload: ApiErrorPayload | null = null;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = null;
    }
    throw new ApiError(
      payload?.error.message ?? `Error ${response.status}`,
      payload?.error.code ?? "api_error",
      response.status,
      payload?.error.details,
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function apiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  if (path.startsWith("/api/")) {
    return path;
  }
  return `${API_BASE}${path}`;
}

export const api = {
  health: () => apiFetch<{ status: string; version: string; ffmpeg: boolean }>("/health"),
  listBooks: (params: { q?: string; sort?: string; limit?: number; offset?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.q) search.set("q", params.q);
    if (params.sort) search.set("sort", params.sort);
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    if (params.offset !== undefined) search.set("offset", String(params.offset));
    const suffix = search.toString();
    return apiFetch<BookList>(`/books${suffix ? `?${suffix}` : ""}`);
  },
  getBook: (bookId: string) => apiFetch<BookDetail>(`/books/${bookId}`),
  deleteBook: (bookId: string) => apiFetch<void>(`/books/${bookId}`, { method: "DELETE" }),
  rescan: () => apiFetch<{ count: number }>("/books/rescan", { method: "POST" }),
  importBook: (file: File) => {
    const data = new FormData();
    data.append("file", file, file.name);
    return apiFetch<Book>("/books/import", { method: "POST", body: data });
  },
  startConversion: (bookId: string, input: ConversionInput) =>
    apiFetch<{ job_id: string }>(`/books/${bookId}/convert`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  getJob: (jobId: string) => apiFetch<Job>(`/jobs/${jobId}`),
  cancelJob: (jobId: string) => apiFetch<Job>(`/jobs/${jobId}/cancel`, { method: "POST" }),
  resumeJob: (jobId: string) =>
    apiFetch<{ job_id: string }>(`/jobs/${jobId}/resume`, { method: "POST" }),
  getVoices: () => apiFetch<Voice[]>("/voices"),
  previewVoice: (input: {
    voice: string;
    engine: string;
    style?: string;
    rate?: string;
    text: string;
  }) =>
    apiFetch<Preview>("/voices/preview", {
      method: "POST",
      body: JSON.stringify({
        voice: input.voice,
        engine: input.engine,
        style: input.style ?? "neutral",
        rate: input.rate ?? "-10%",
        text: input.text,
      }),
    }),
  getSettings: () => apiFetch<Settings>("/settings"),
  updateSettings: (input: Partial<Settings>) =>
    apiFetch<Settings>("/settings", {
      method: "PUT",
      body: JSON.stringify(input),
    }),
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Ocurrió un error inesperado.";
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}
