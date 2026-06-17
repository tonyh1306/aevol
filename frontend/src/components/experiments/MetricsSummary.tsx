import type { MetricAggregate } from "@/lib/types";

export function MetricsSummary({ metrics }: { metrics: MetricAggregate[] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {metrics.map((m) => (
        <div key={m.name} className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{m.name}</p>
          <p className="text-xl font-semibold text-gray-900">{m.mean.toFixed(3)}</p>
          <div className="flex gap-3 mt-1 text-xs text-gray-400">
            <span>p95: {m.p95.toFixed(3)}</span>
            <span>n={m.count}</span>
          </div>
          {m.unit && <p className="text-xs text-gray-400 mt-0.5">{m.unit}</p>}
        </div>
      ))}
    </div>
  );
}
