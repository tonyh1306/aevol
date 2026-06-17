"use client";
import useSWR from "swr";
import { api } from "@/lib/api";

export function useWorkers() {
  return useSWR("workers", () => api.workers.list(), { refreshInterval: 5000 });
}
