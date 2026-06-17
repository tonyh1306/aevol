"use client";
import { useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useExperiment, useExperimentTasks, useExperimentMetrics } from "@/hooks/useExperiments";
import { useSSE } from "@/hooks/useSSE";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { TaskProgressBar } from "@/components/experiments/TaskProgressBar";
import { EmptyState } from "@/components/shared/EmptyState";
import { MetricsSummary } from "@/components/experiments/MetricsSummary";
import { api } from "@/lib/api";
import { formatDate, formatDuration } from "@/lib/utils";
import type { SSEEvent } from "@/lib/types";
import { Play, X, GitBranch, BarChart2 } from "lucide-react";

export default function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: exp, mutate: mutateExp } = useExperiment(id);
  const { data: tasks, mutate: mutateTasks } = useExperimentTasks(id);
  const { data: metrics } = useExperimentMetrics(id);

  // Live SSE updates
  const handleSSE = useCallback((event: SSEEvent) => {
    if (event.event === "task_completed" || event.event === "task_failed") {
      mutateTasks();
      mutateExp();
    }
  }, [mutateTasks, mutateExp]);
  useSSE(`/api/v1/stream/experiments/${id}`, handleSSE);

  const [statusFilter, setStatusFilter] = useState("");

  if (!exp) return <div className="text-gray-400 text-sm">Loading…</div>;

  const canRun = exp.status === "draft" || exp.status === "failed";
  const canCancel = exp.status === "running";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold">{exp.name}</h1>
            <StatusBadge status={exp.status} />
            <span className="text-xs text-gray-400">v{exp.version}</span>
          </div>
          {exp.description && <p className="text-sm text-gray-500 mt-1">{exp.description}</p>}
          <div className="flex gap-2 mt-2">
            {exp.tags.map(t => (
              <span key={t} className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">{t}</span>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          {canRun && (
            <button onClick={() => api.experiments.run(id).then(() => mutateExp())}
              className="flex items-center gap-1.5 bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-blue-700">
              <Play size={14} /> Run
            </button>
          )}
          {canCancel && (
            <button onClick={() => api.experiments.cancel(id).then(() => mutateExp())}
              className="flex items-center gap-1.5 border border-red-300 text-red-600 px-3 py-1.5 rounded-lg text-sm hover:bg-red-50">
              <X size={14} /> Cancel
            </button>
          )}
          <button onClick={() => api.experiments.clone(id).then(() => window.history.back())}
            className="flex items-center gap-1.5 border border-gray-300 text-gray-600 px-3 py-1.5 rounded-lg text-sm hover:bg-gray-50">
            <GitBranch size={14} /> Clone
          </button>
          <Link href={`/experiments/${id}/compare`}
            className="flex items-center gap-1.5 border border-gray-300 text-gray-600 px-3 py-1.5 rounded-lg text-sm hover:bg-gray-50">
            <BarChart2 size={14} /> Compare
          </Link>
        </div>
      </div>

      {/* Progress */}
      {exp.total_tasks > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Progress</h2>
          <TaskProgressBar total={exp.total_tasks} completed={exp.completed_tasks} failed={exp.failed_tasks} />
          <div className="flex gap-6 mt-3 text-xs text-gray-500">
            <span>Started: {exp.started_at ? formatDate(exp.started_at) : "—"}</span>
            <span>Completed: {exp.completed_at ? formatDate(exp.completed_at) : "—"}</span>
          </div>
          {exp.status === "running" && (
            <div className="flex items-center gap-1.5 mt-2 text-xs text-blue-600">
              <span className="w-2 h-2 bg-blue-500 rounded-full pulse-dot" />
              Live updates via SSE
            </div>
          )}
        </div>
      )}

      {/* Metrics */}
      {metrics && metrics.metrics.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Metrics</h2>
          <MetricsSummary metrics={metrics.metrics} />
        </div>
      )}

      {/* Tasks */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-medium text-gray-700">Tasks ({tasks?.total ?? 0})</h2>
          <div className="flex gap-1">
            {["", "PENDING", "RUNNING", "COMPLETED", "FAILED", "DEAD"].map(s => (
              <button key={s} onClick={() => setStatusFilter(s)}
                className={`px-2 py-0.5 text-xs rounded ${statusFilter === s ? "bg-blue-600 text-white" : "text-gray-500 hover:bg-gray-100"}`}>
                {s || "All"}
              </button>
            ))}
          </div>
        </div>
        {!tasks?.items.length ? (
          <EmptyState title="No tasks" description="Run the experiment to generate tasks." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Task ID", "Status", "Attempt", "Latency", "Cost", "Worker", "Completed"].map(h => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tasks.items
                .filter(t => !statusFilter || t.status === statusFilter)
                .slice(0, 100)
                .map(task => (
                <tr key={task.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs text-gray-500">{task.id.slice(0, 8)}…</td>
                  <td className="px-4 py-2"><StatusBadge status={task.status} /></td>
                  <td className="px-4 py-2 text-gray-500">{task.attempt_count}</td>
                  <td className="px-4 py-2 text-gray-500">{task.latency_ms ? formatDuration(task.latency_ms) : "—"}</td>
                  <td className="px-4 py-2 text-gray-500">{task.cost_usd ? `$${parseFloat(task.cost_usd).toFixed(5)}` : "—"}</td>
                  <td className="px-4 py-2 text-xs text-gray-400">{task.worker_id?.slice(0, 8) ?? "—"}</td>
                  <td className="px-4 py-2 text-xs text-gray-400">{task.completed_at ? formatDate(task.completed_at) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
