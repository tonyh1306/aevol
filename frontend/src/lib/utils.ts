export function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

export function progressPct(completed: number, total: number): number {
  if (total === 0) return 0;
  return Math.round((completed / total) * 100);
}

export function statusColor(status: string): string {
  switch (status) {
    case "completed": case "COMPLETED": return "bg-green-100 text-green-800";
    case "running": case "RUNNING": return "bg-blue-100 text-blue-800";
    case "failed": case "FAILED": return "bg-red-100 text-red-800";
    case "DEAD": return "bg-red-200 text-red-900";
    case "pending": case "PENDING": return "bg-yellow-100 text-yellow-800";
    case "draft": return "bg-gray-100 text-gray-700";
    case "cancelled": return "bg-gray-200 text-gray-600";
    default: return "bg-gray-100 text-gray-700";
  }
}

export function workerStatusColor(status: string): string {
  switch (status) {
    case "busy": return "bg-blue-500";
    case "idle": return "bg-green-500";
    case "draining": return "bg-yellow-500";
    case "dead": return "bg-red-500";
    default: return "bg-gray-400";
  }
}
