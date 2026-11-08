import { fetchEventSource } from "@microsoft/fetch-event-source";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { api, apiUrl, authHeaders } from "./client";
import type {
  BookmarkInput,
  BookPreferences,
  ConversionInput,
  Job,
  ReadingStateInput,
  Settings,
} from "./types";

export const queryKeys = {
  books: (params: { q?: string; sort?: string } = {}) => ["books", params] as const,
  book: (id: string) => ["book", id] as const,
  job: (id: string) => ["job", id] as const,
  voices: ["voices"] as const,
  settings: ["settings"] as const,
  readerManifest: (bookId: string) => ["reader-manifest", bookId] as const,
  readerChapter: (bookId: string, chapterIndex: number) =>
    ["reader-chapter", bookId, chapterIndex] as const,
  readerState: (bookId: string) => ["reader-state", bookId] as const,
  readingState: (bookId: string) => ["reading-state", bookId] as const,
  bookPreferences: (bookId: string) => ["book-preferences", bookId] as const,
  bookSearch: (bookId: string, query: string) => ["book-search", bookId, query] as const,
  bookmarks: (bookId: string) => ["bookmarks", bookId] as const,
};

export function useBooks(params: { q?: string; sort?: string } = {}) {
  return useQuery({
    queryKey: queryKeys.books(params),
    queryFn: () => api.listBooks({ ...params, limit: 100 }),
  });
}

export function useBook(bookId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.book(bookId ?? ""),
    queryFn: () => api.getBook(bookId as string),
    enabled: Boolean(bookId),
  });
}

export function useVoices() {
  return useQuery({
    queryKey: queryKeys.voices,
    queryFn: api.getVoices,
    staleTime: 60_000,
  });
}

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: api.getSettings,
    staleTime: 30_000,
  });
}

export function useImportBook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.importBook,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["books"] });
    },
  });
}

export function useDeleteBook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.deleteBook,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["books"] });
    },
  });
}

export function useRescan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.rescan,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["books"] });
    },
  });
}

export function useStartConversion(bookId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ConversionInput) => api.startConversion(bookId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.book(bookId) });
      void queryClient.invalidateQueries({ queryKey: ["books"] });
    },
  });
}

export function useCancelJob(bookId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.cancelJob,
    onSuccess: (job) => {
      queryClient.setQueryData(queryKeys.job(job.id), job);
      void queryClient.invalidateQueries({ queryKey: queryKeys.book(bookId) });
    },
  });
}

export function useResumeJob(bookId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.resumeJob,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.book(bookId) });
      void queryClient.invalidateQueries({ queryKey: ["books"] });
    },
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: Partial<Settings>) => api.updateSettings(input),
    onSuccess: (settings) => {
      queryClient.setQueryData(queryKeys.settings, settings);
    },
  });
}

const TERMINAL = new Set(["completed", "failed", "cancelled", "interrupted"]);

export function useJobEvents(jobId: string | null | undefined, bookId: string) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!jobId) {
      return;
    }
    const controller = new AbortController();
    let closed = false;

    fetchEventSource(apiUrl(`/jobs/${jobId}/events`), {
      headers: authHeaders(),
      signal: controller.signal,
      openWhenHidden: true,
      onmessage(message) {
        if (message.event !== "job") {
          return;
        }
        try {
          const job = JSON.parse(message.data) as Job;
          queryClient.setQueryData(queryKeys.job(job.id), job);
          if (TERMINAL.has(job.status)) {
            void queryClient.invalidateQueries({ queryKey: queryKeys.book(bookId) });
            void queryClient.invalidateQueries({ queryKey: ["books"] });
            controller.abort();
          }
        } catch {
          // Ignore malformed SSE frames; the next snapshot is authoritative.
        }
      },
      onclose() {
        if (!closed) {
          closed = true;
          void queryClient.invalidateQueries({ queryKey: queryKeys.book(bookId) });
        }
        throw new Error("SSE closed");
      },
      onerror(error) {
        throw error;
      },
    }).catch(() => {
      // The job query remains the source of truth on stream failures.
    });

    return () => {
      closed = true;
      controller.abort();
    };
  }, [bookId, jobId, queryClient]);
}

export function useJob(jobId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.job(jobId ?? ""),
    queryFn: () => api.getJob(jobId as string),
    enabled: Boolean(jobId),
  });
}

export function useReaderManifest(bookId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.readerManifest(bookId ?? ""),
    queryFn: () => api.getManifest(bookId as string),
    enabled: Boolean(bookId),
    staleTime: 30_000,
  });
}

export function useReaderChapter(bookId: string | undefined, chapterIndex: number) {
  return useQuery({
    queryKey: queryKeys.readerChapter(bookId ?? "", chapterIndex),
    queryFn: () => api.getChapter(bookId as string, chapterIndex),
    enabled: Boolean(bookId) && chapterIndex > 0,
  });
}

export function useReaderState(bookId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.readerState(bookId ?? ""),
    queryFn: () => api.getReaderState(bookId as string),
    enabled: Boolean(bookId),
  });
}

export function useSaveReaderState(bookId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (state: { position_ms: number; chapter_index: number; playback_rate: number }) =>
      api.saveReaderState(bookId, state),
    onSuccess: (state) => {
      queryClient.setQueryData(queryKeys.readerState(bookId), state);
    },
  });
}

export function useReadingState(bookId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.readingState(bookId ?? ""),
    queryFn: () => api.getReadingState(bookId as string),
    enabled: Boolean(bookId),
  });
}

export function useSaveReadingState(bookId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (state: ReadingStateInput) => api.saveReadingState(bookId, state),
    onSuccess: (state) => {
      queryClient.setQueryData(queryKeys.readingState(bookId), state);
    },
  });
}

export function useBookPreferences(bookId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.bookPreferences(bookId ?? ""),
    queryFn: () => api.getBookPreferences(bookId as string),
    enabled: Boolean(bookId),
  });
}

export function useUpdateBookPreferences(bookId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: Partial<BookPreferences>) => api.updateBookPreferences(bookId, input),
    onSuccess: (preferences) => {
      queryClient.setQueryData(queryKeys.bookPreferences(bookId), preferences);
    },
  });
}

export function useBookSearch(bookId: string | undefined, query: string) {
  const term = query.trim();
  return useQuery({
    queryKey: queryKeys.bookSearch(bookId ?? "", term),
    queryFn: () => api.searchBook(bookId as string, term),
    enabled: Boolean(bookId) && term.length >= 2,
    staleTime: 10_000,
  });
}

export function useBookmarks(bookId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.bookmarks(bookId ?? ""),
    queryFn: () => api.listBookmarks(bookId as string),
    enabled: Boolean(bookId),
  });
}

export function useCreateBookmark(bookId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: BookmarkInput) => api.createBookmark(bookId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.bookmarks(bookId) });
    },
  });
}

export function useDeleteBookmark(bookId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (bookmarkId: number) => api.deleteBookmark(bookId, bookmarkId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.bookmarks(bookId) });
    },
  });
}
