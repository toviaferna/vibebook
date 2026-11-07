import { fetchEventSource } from "@microsoft/fetch-event-source";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { api, apiUrl, authHeaders } from "./client";
import type { ConversionInput, Job, Settings } from "./types";

export const queryKeys = {
  books: (params: { q?: string; sort?: string } = {}) => ["books", params] as const,
  book: (id: string) => ["book", id] as const,
  job: (id: string) => ["job", id] as const,
  voices: ["voices"] as const,
  settings: ["settings"] as const,
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
