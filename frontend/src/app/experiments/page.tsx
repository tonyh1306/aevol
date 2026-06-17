"use client";
import { useState } from "react";
import Link from "next/link";
import { useExperiments } from "@/hooks/useExperiments";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { TaskProgressBar } from "@/components/experiments/TaskProgressBar";
import { EmptyState } from "@/components/shared/EmptyState";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Plus, RefreshCw, GitBranch } from "lucide-react";
import type { Experiment } from "@/lib/types";

const STATUS_FILTERS = ["", "draft", "running", "completed", "failed"];

export default function ExperimentsPage() {
  const [status, setStatus] = useState("");
  const { data, isLoading, mutate } = useExperiments({ status: status || undefined });

  async function handleRun(id: string) {
    await api.experiments.run(id);
    mutate();
  }

  async function handleClone(id: string) {
    await api.experiments.clone(id);
    mutate();
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900">Experiments</h1>
        <Link
          href="/experiments/new"
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
        >
          <Plus size={16} /> New Experiment
        </Link>
      </div>

      <div className="flex gap-2 mb-4">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`px-3 py-1 rounded-full text-xs border transition-colors ${
              status === s ? "bg-blue-600 text-white border-blue-600" : "border-gray-300 text-gray-600 hover:border-blue-400"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="py-12 text-center text-gray-400 text-sm">Loading…</div>
        ) : !data?.items.length ? (
          <EmptyState title="No experiments yet" description="Create your first experiment to get started." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Name", "Status", "Dataset", "Progress", "Created", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.items.map((exp: Experiment) => (
                <tr key={exp.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link href={`/experiments/${exp.id}`} className="text-blue-600 hover:underline font-medium">
                      {exp.name}
                    </Link>
                    <div className="text-xs text-gray-400 mt-0.5">v{exp.version}</div>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={exp.status} /></td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{exp.dataset_id ? "Attached" : "—"}</td>
                  <td className="px-4 py-3 w-48">
                    {exp.total_tasks > 0 ? (
                      <TaskProgressBar total={exp.total_tasks} completed={exp.completed_tasks} failed={exp.failed_tasks} />
                    ) : <span className="text-gray-400 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">{formatDate(exp.created_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      {exp.status === "draft" && (
                        <button onClick={() => handleRun(exp.id)} className="text-xs text-blue-600 hover:underline">Run</button>
                      )}
                      <button onClick={() => handleClone(exp.id)} className="text-xs text-gray-500 hover:underline flex items-center gap-1">
                        <GitBranch size={12} /> Clone
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="mt-3 text-xs text-gray-400">
        {data?.total ?? 0} total experiment{data?.total !== 1 ? "s" : ""}
      </div>
    </div>
  );
}
