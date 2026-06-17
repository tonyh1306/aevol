"use client";
import { useWorkers } from "@/hooks/useWorkers";
import { workerStatusColor, formatDate } from "@/lib/utils";
import { EmptyState } from "@/components/shared/EmptyState";
import { Cpu } from "lucide-react";

export default function WorkersPage() {
  const { data, isLoading } = useWorkers();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Workers</h1>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="w-2 h-2 bg-green-500 rounded-full pulse-dot" />
          Auto-refreshes every 5s
        </div>
      </div>

      {isLoading ? (
        <div className="text-gray-400 text-sm">Loading…</div>
      ) : !data?.items.length ? (
        <EmptyState title="No workers registered" description="Start worker containers to begin processing tasks." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.items.map(w => {
            const heartbeatAge = Math.round((Date.now() - new Date(w.last_heartbeat).getTime()) / 1000);
            const stale = heartbeatAge > 30;
            return (
              <div key={w.id} className={`bg-white border rounded-xl p-4 space-y-3 ${stale ? "border-red-200" : "border-gray-200"}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`w-2.5 h-2.5 rounded-full ${workerStatusColor(w.status)} ${w.status === "busy" ? "pulse-dot" : ""}`} />
                    <span className="text-sm font-medium">{w.hostname}</span>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    w.status === "busy" ? "bg-blue-100 text-blue-700" :
                    w.status === "idle" ? "bg-green-100 text-green-700" :
                    w.status === "dead" ? "bg-red-100 text-red-700" :
                    "bg-gray-100 text-gray-600"
                  }`}>{w.status}</span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
                  <div><span className="font-medium">PID</span> {w.pid}</div>
                  <div><span className="font-medium">Ver</span> {w.version ?? "—"}</div>
                  <div><span className="font-medium">CPU</span> {w.cpu_percent != null ? `${w.cpu_percent.toFixed(1)}%` : "—"}</div>
                  <div><span className="font-medium">Mem</span> {w.memory_mb != null ? `${w.memory_mb} MB` : "—"}</div>
                  <div><span className="font-medium">Done</span> {w.tasks_completed}</div>
                  <div><span className="font-medium">Failed</span> {w.tasks_failed}</div>
                </div>

                {w.current_task_id && (
                  <div className="text-xs text-blue-600 bg-blue-50 rounded px-2 py-1 flex items-center gap-1">
                    <Cpu size={10} /> Processing {w.current_task_id.slice(0, 8)}…
                  </div>
                )}

                <div className={`text-xs ${stale ? "text-red-500" : "text-gray-400"}`}>
                  Heartbeat: {heartbeatAge}s ago {stale && "⚠ stale"}
                </div>

                <div className="flex flex-wrap gap-1">
                  {w.capabilities.map(c => (
                    <span key={c} className="bg-gray-100 text-gray-500 text-xs px-1.5 py-0.5 rounded">{c}</span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
