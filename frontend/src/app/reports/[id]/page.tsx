"use client";
import { useParams } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const { data: report, isLoading } = useSWR(["report", id], () => api.reports.get(id));

  if (isLoading) return <div className="text-gray-400 text-sm">Loading…</div>;
  if (!report) return <div className="text-gray-400 text-sm">Report not found.</div>;

  const { summary, regression_flags } = report;

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold">{report.title}</h1>
        <p className="text-xs text-gray-400 mt-1">Generated {formatDate(report.generated_at)}</p>
      </div>

      {/* Summary chips */}
      <div className="flex gap-3">
        <Chip label="Regressions" value={summary.regression_count} color="red" />
        <Chip label="Improvements" value={summary.improvements?.length ?? 0} color="green" />
        <Chip label="Stable" value={summary.stable?.length ?? 0} color="gray" />
      </div>

      {/* Regression flags */}
      {regression_flags.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-red-700 mb-3">Regression Flags</h2>
          <div className="space-y-2">
            {regression_flags.map((r) => (
              <div key={r.metric} className="bg-white border border-red-100 rounded-lg px-3 py-2 text-sm flex items-center justify-between">
                <span className="font-medium">{r.metric}</span>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-gray-500">{r.baseline_value.toFixed(4)} → {r.candidate_value.toFixed(4)}</span>
                  <span className="text-red-600 font-bold">{r.delta_pct.toFixed(1)}%</span>
                  <span className={`px-1.5 rounded ${r.severity === "critical" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>
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
        <div className="px-4 py-3 border-b border-gray-100 text-sm font-medium text-gray-700">All Metric Deltas</div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {["Metric", "Baseline", "Candidate", "Delta"].map(h => (
                <th key={h} className="px-4 py-2 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {summary.deltas?.map((d) => (
              <tr key={d.metric} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{d.metric}</td>
                <td className="px-4 py-2 text-gray-500">{d.baseline.toFixed(4)}</td>
                <td className="px-4 py-2 text-gray-500">{d.candidate.toFixed(4)}</td>
                <td className={`px-4 py-2 font-semibold ${d.delta_pct > 0 ? "text-green-600" : d.delta_pct < 0 ? "text-red-600" : "text-gray-500"}`}>
                  {d.delta_pct > 0 ? "+" : ""}{d.delta_pct.toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-gray-400 flex gap-4">
        <span>Baseline: <Link href={`/experiments/${report.baseline_id}`} className="text-blue-500 hover:underline">{report.baseline_id.slice(0, 8)}</Link></span>
        <span>Candidate: <Link href={`/experiments/${report.candidate_id}`} className="text-blue-500 hover:underline">{report.candidate_id.slice(0, 8)}</Link></span>
      </div>
    </div>
  );
}

function Chip({ label, value, color }: { label: string; value: number; color: "red" | "green" | "gray" }) {
  const colors = { red: "bg-red-100 text-red-700", green: "bg-green-100 text-green-700", gray: "bg-gray-100 text-gray-600" };
  return (
    <div className={`px-3 py-1.5 rounded-lg text-sm ${colors[color]}`}>
      <span className="font-bold">{value}</span> {label}
    </div>
  );
}
