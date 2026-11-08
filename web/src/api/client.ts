import type {
  ApiErrorPayload,
  Book,
  BookDetail,
  BookList,
  Bookmark,
  BookmarkInput,
  BookmarkList,
  BookPreferences,
  ChapterPayload,
  ConversionInput,
  EngineList,
  Job,
  Manifest,
  Preview,
  ReaderState,
  ReadingBookmark,
  ReadingBookmarkInput,
  ReadingBookmarkList,
  ReadingState,
  ReadingStateInput,
  SearchResponse,
  Settings,
  Voice,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";
const API_TOKEN = import.meta.env.VITE_API_TOKEN as string | undefined;

let apiBase = normalizeBase(API_BASE);
let apiToken = API_TOKEN ?? "";

function normalizeBase(value: string): string {
  const trimmed = value.replace(/\/+$/, "");
  if (!trimmed) {
    return "/api";
  }
  return trimmed.endsWith("/api") ? trimmed : `${trimmed}/api`;
}

export function configureApi(config: { baseUrl: string; token: string }): void {
  apiBase = normalizeBase(config.baseUrl);
  apiToken = config.token;
}

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
  return apiToken ? { "X-Vibebook-Token": apiToken } : {};
}

function headersFor(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers);
  if (apiToken) {
    headers.set("X-Vibebook-Token", apiToken);
  }
  return headers;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = headersFor(init);
  const body = init.body;
  if (body && typeof body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${apiBase}${path}`, {
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
  const normalized = path.startsWith("/api/") ? path.slice(4) : path;
  const url = `${apiBase}${normalized}`;
  if (!apiToken) {
    return url;
  }
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}token=${encodeURIComponent(apiToken)}`;
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
  getEngines: () => apiFetch<EngineList>("/engines"),
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
  getManifest: (bookId: string) => apiFetch<Manifest>(`/books/${bookId}/manifest`),
  getChapter: (bookId: string, chapterIndex: number) =>
    apiFetch<ChapterPayload>(`/books/${bookId}/chapters/${chapterIndex}`),
  getReaderState: (bookId: string) => apiFetch<ReaderState>(`/books/${bookId}/state`),
  saveReaderState: (
    bookId: string,
    state: Pick<ReaderState, "position_ms" | "chapter_index" | "playback_rate">,
  ) =>
    apiFetch<ReaderState>(`/books/${bookId}/state`, {
      method: "PUT",
      body: JSON.stringify(state),
    }),
  getReadingState: (bookId: string) => apiFetch<ReadingState>(`/books/${bookId}/reading-state`),
  saveReadingState: (bookId: string, state: ReadingStateInput) =>
    apiFetch<ReadingState>(`/books/${bookId}/reading-state`, {
      method: "PUT",
      body: JSON.stringify(state),
    }),
  listReadingBookmarks: (bookId: string) =>
    apiFetch<ReadingBookmarkList>(`/books/${bookId}/reading-bookmarks`),
  createReadingBookmark: (bookId: string, input: ReadingBookmarkInput) =>
    apiFetch<ReadingBookmark>(`/books/${bookId}/reading-bookmarks`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  deleteReadingBookmark: (bookId: string, bookmarkId: number) =>
    apiFetch<void>(`/books/${bookId}/reading-bookmarks/${bookmarkId}`, {
      method: "DELETE",
    }),
  getBookPreferences: (bookId: string) => apiFetch<BookPreferences>(`/books/${bookId}/preferences`),
  updateBookPreferences: (bookId: string, input: Partial<BookPreferences>) =>
    apiFetch<BookPreferences>(`/books/${bookId}/preferences`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  searchBook: (bookId: string, query: string) =>
    apiFetch<SearchResponse>(`/books/${bookId}/search?q=${encodeURIComponent(query)}`),
  listBookmarks: (bookId: string) => apiFetch<BookmarkList>(`/books/${bookId}/bookmarks`),
  createBookmark: (bookId: string, input: BookmarkInput) =>
    apiFetch<Bookmark>(`/books/${bookId}/bookmarks`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  deleteBookmark: (bookId: string, bookmarkId: number) =>
    apiFetch<void>(`/books/${bookId}/bookmarks/${bookmarkId}`, { method: "DELETE" }),
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
