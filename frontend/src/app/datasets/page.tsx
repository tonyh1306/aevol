"use client";
import { useRef, useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatDate, formatBytes } from "@/lib/utils";
import { Upload } from "lucide-react";
import Link from "next/link";
import type { Dataset } from "@/lib/types";

export default function DatasetsPage() {
  const { data, isLoading, mutate } = useSWR("datasets", () => api.datasets.list());
  const [uploading, setUploading] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file || !uploadName.trim()) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("name", uploadName);
      await api.datasets.upload(fd);
      mutate();
      setUploadName("");
      if (fileRef.current) fileRef.current.value = "";
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Datasets</h1>

      {/* Upload card */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-medium text-gray-700">Upload Dataset</h2>
        <div className="flex gap-3">
          <input
            type="text" placeholder="Dataset name" value={uploadName}
            onChange={e => setUploadName(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input type="file" accept=".csv,.jsonl" ref={fileRef}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          <button onClick={handleUpload} disabled={uploading || !uploadName.trim()}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-40">
            <Upload size={14} /> {uploading ? "Uploading…" : "Upload"}
          </button>
        </div>
        <p className="text-xs text-gray-400">Supported formats: CSV, JSONL. Max 100MB.</p>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="py-12 text-center text-gray-400 text-sm">Loading…</div>
        ) : !data?.items.length ? (
          <EmptyState title="No datasets yet" description="Upload a CSV or JSONL file to get started." />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {["Name", "Format", "Rows", "Size", "Uploaded"].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.items.map((d: Dataset) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link href={`/datasets/${d.id}`} className="text-blue-600 hover:underline font-medium">{d.name}</Link>
                  </td>
                  <td className="px-4 py-3"><span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded">{d.format}</span></td>
                  <td className="px-4 py-3 text-gray-500">{d.row_count ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-500">{d.file_size ? formatBytes(d.file_size) : "—"}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{formatDate(d.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
