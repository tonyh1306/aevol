"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/shared/EmptyState";
import type { Experiment } from "@/lib/types";

export default function ComparePage() {
  const { id } = useParams<{ id: string }>();
  const [candidateId, setCandidateId] = useState("");

  const { data: experiments } = useSWR("all-experiments", () => api.experiments.list({ limit: 100 }));
  const { data: comparison, isLoading } = useSWR(
    candidateId ? ["compare", id, candidateId] : null,
    () => api.experiments.compare(id, candidateId)
  );

  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-xl font-semibold">Experiment Comparison</h1>

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-500 uppercase font-medium">Baseline</label>
            <p className="text-sm text-gray-700 mt-1">{experiments?.items.find((e: Experiment) => e.id === id)?.name ?? id.slice(0, 8)}</p>
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase font-medium">Candidate</label>
            <select
              className="mt-1 w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={candidateId}
              onChange={e => setCandidateId(e.target.value)}
            >
              <option value="">— Select candidate —</option>
              {experiments?.items
                .filter((e: Experiment) => e.id !== id && ["completed", "failed"].includes(e.status))
                .map((e: Experiment) => (
                  <option key={e.id} value={e.id}>{e.name} (v{e.version})</option>
                ))}
            </select>
          </div>
        </div>
      </div>

      {isLoading && <p className="text-gray-400 text-sm">Computing comparison…</p>}

      {comparison && !isLoading && (
        <div className="space-y-4">
          {/* Regressions */}
          {comparison.regressions.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <h2 className="text-sm font-semibold text-red-700 mb-3">Regressions ({comparison.regressions.length})</h2>
              <div className="space-y-2">
                {comparison.regressions.map(r => (
                  <div key={r.metric} className="flex items-center justify-between bg-white border border-red-100 rounded-lg px-3 py-2 text-sm">
                    <span className="font-medium text-gray-700">{r.metric}</span>
                    <div className="flex items-center gap-4 text-xs">
                      <span className="text-gray-500">baseline: {r.baseline_value.toFixed(3)}</span>
                      <span className="text-gray-500">candidate: {r.candidate_value.toFixed(3)}</span>
                      <span className={`font-bold ${r.delta_pct < 0 ? "text-red-600" : "text-green-600"}`}>
                        {r.delta_pct > 0 ? "+" : ""}{r.delta_pct.toFixed(1)}%
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-xs ${r.severity === "critical" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>
                        {r.severity}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* All deltas */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="text-sm font-medium text-gray-700">All Metric Deltas</h2>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  {["Metric", "Baseline", "Candidate", "Delta"].map(h => (
                    <th key={h} className="px-4 py-2 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {comparison.deltas.map(d => (
                  <tr key={d.metric} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{d.metric}</td>
                    <td className="px-4 py-2 text-gray-500">{d.baseline.toFixed(4)}</td>
                    <td className="px-4 py-2 text-gray-500">{d.candidate.toFixed(4)}</td>
                    <td className={`px-4 py-2 font-semibold ${
                      d.delta_pct > 0 ? "text-green-600" : d.delta_pct < 0 ? "text-red-600" : "text-gray-500"
                    }`}>
                      {d.delta_pct > 0 ? "+" : ""}{d.delta_pct.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!candidateId && <EmptyState title="Select a candidate experiment" description="Choose a completed experiment to compare against this baseline." />}
    </div>
  );
}
