"use client";
import { useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { api } from "@/lib/api";
import { formatDate, formatBytes } from "@/lib/utils";

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [page, setPage] = useState(1);

  const { data: dataset } = useSWR(["dataset", id], () => api.datasets.get(id));
  const { data: rows } = useSWR(["dataset-rows", id, page], () => api.datasets.rows(id, { page, limit: 25 }));

  if (!dataset) return <div className="text-gray-400 text-sm">Loading…</div>;

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-xl font-semibold">{dataset.name}</h1>
        {dataset.description && <p className="text-sm text-gray-500 mt-1">{dataset.description}</p>}
        <div className="flex gap-4 mt-2 text-sm text-gray-500">
          <span><strong>Format:</strong> {dataset.format.toUpperCase()}</span>
          <span><strong>Rows:</strong> {dataset.row_count ?? "—"}</span>
          <span><strong>Size:</strong> {dataset.file_size ? formatBytes(dataset.file_size) : "—"}</span>
          <span><strong>Uploaded:</strong> {formatDate(dataset.created_at)}</span>
        </div>
        {dataset.schema_info && (
          <div className="mt-2">
            <span className="text-xs text-gray-400">Columns: </span>
            {(dataset.schema_info.columns as string[] | undefined)?.map((c) => (
              <span key={c} className="bg-gray-100 text-gray-600 text-xs px-1.5 py-0.5 rounded mr-1">{c}</span>
            ))}
          </div>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 text-sm font-medium text-gray-700">
          Data Preview ({rows?.total ?? 0} rows)
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead className="bg-gray-50 text-gray-500">
              <tr>
                <th className="px-3 py-2 text-left">#</th>
                <th className="px-3 py-2 text-left">Input</th>
                <th className="px-3 py-2 text-left">Expected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows?.items.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-gray-400">{row.row_index}</td>
                  <td className="px-3 py-2 max-w-sm truncate text-gray-700">
                    {JSON.stringify(row.input_data).slice(0, 120)}
                  </td>
                  <td className="px-3 py-2 text-gray-500">
                    {row.expected ? JSON.stringify(row.expected).slice(0, 80) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows && rows.total > 25 && (
          <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
            <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
              className="text-sm text-blue-600 disabled:text-gray-300">← Prev</button>
            <span className="text-xs text-gray-400">Page {page} of {Math.ceil(rows.total / 25)}</span>
            <button disabled={page >= Math.ceil(rows.total / 25)} onClick={() => setPage(p => p + 1)}
              className="text-sm text-blue-600 disabled:text-gray-300">Next →</button>
          </div>
        )}
      </div>
    </div>
  );
}
