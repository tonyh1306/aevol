"use client";
import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatDate } from "@/lib/utils";
import { useExperiments } from "@/hooks/useExperiments";
import type { Experiment, Report } from "@/lib/types";

export default function ReportsPage() {
  const { data, mutate } = useSWR("reports", () => api.reports.list());
  const { data: experiments } = useExperiments({ status: "completed" });

  const [baselineId, setBaselineId] = useState("");
  const [candidateId, setCandidateId] = useState("");
  const [generating, setGenerating] = useState(false);

  async function generate() {
    if (!baselineId || !candidateId) return;
    setGenerating(true);
    try {
      await api.reports.create(baselineId, candidateId);
      mutate();
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-xl font-semibold">Reports</h1>

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <h2 className="text-sm font-medium text-gray-700 mb-3">Generate New Report</h2>
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="text-xs text-gray-500 mb-1 block">Baseline Experiment</label>
            <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={baselineId} onChange={e => setBaselineId(e.target.value)}>
              <option value="">— Select —</option>
              {experiments?.items.map((e: Experiment) => <option key={e.id} value={e.id}>{e.name}</option>)}
            </select>
          </div>
          <div className="flex-1">
            <label className="text-xs text-gray-500 mb-1 block">Candidate Experiment</label>
            <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" value={candidateId} onChange={e => setCandidateId(e.target.value)}>
              <option value="">— Select —</option>
              {experiments?.items.filter((e: Experiment) => e.id !== baselineId).map((e: Experiment) => <option key={e.id} value={e.id}>{e.name}</option>)}
            </select>
          </div>
          <button onClick={generate} disabled={generating || !baselineId || !candidateId}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-40 whitespace-nowrap">
            {generating ? "Generating…" : "Generate Report"}
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {!data?.items.length ? (
          <EmptyState title="No reports yet" description="Generate a regression report by selecting two completed experiments." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {["Title", "Regressions", "Generated"].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.items.map((r: Report) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link href={`/reports/${r.id}`} className="text-blue-600 hover:underline">{r.title}</Link>
                  </td>
                  <td className="px-4 py-3">
                    {r.regression_flags.length > 0 ? (
                      <span className="text-red-600 font-medium">{r.regression_flags.length} regression{r.regression_flags.length !== 1 ? "s" : ""}</span>
                    ) : <span className="text-green-600">None</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{formatDate(r.generated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
