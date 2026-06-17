"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { Experiment, MetricSummary } from "@/lib/types";

export function useExperiments(params?: { status?: string; page?: number }) {
  return useSWR(["experiments", params], () => api.experiments.list(params), {
    refreshInterval: 10000,
  });
}

export function useExperiment(id: string | null) {
  return useSWR(id ? ["experiment", id] : null, () => api.experiments.get(id!), {
    refreshInterval: 5000,
  });
}

export function useExperimentMetrics(id: string | null) {
  return useSWR(id ? ["metrics", id] : null, () => api.experiments.metricsSummary(id!));
}

export function useExperimentTasks(id: string | null, params?: { status?: string }) {
  return useSWR(
    id ? ["tasks", id, params] : null,
    () => api.experiments.tasks(id!, params),
    { refreshInterval: 3000 }
  );
}
