"use client";
import { useEffect } from "react";
import type { SSEEvent } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export function useSSE(path: string, onEvent: (event: SSEEvent) => void) {
  useEffect(() => {
    let es: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      es = new EventSource(`${API_BASE}${path}`);
      es.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data) as SSEEvent;
          onEvent(parsed);
        } catch { /* ignore malformed */ }
      };
      es.onerror = () => {
        es?.close();
        retryTimeout = setTimeout(connect, 3000);
      };
    }

    connect();
    return () => {
      es?.close();
      if (retryTimeout) clearTimeout(retryTimeout);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);
}
