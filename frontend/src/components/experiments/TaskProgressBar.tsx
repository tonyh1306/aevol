import { progressPct } from "@/lib/utils";

interface Props {
  total: number;
  completed: number;
  failed: number;
}

export function TaskProgressBar({ total, completed, failed }: Props) {
  const completedPct = progressPct(completed, total);
  const failedPct = progressPct(failed, total);

  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{completed} / {total} tasks</span>
        <span>{completedPct}%</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden flex">
        <div
          className="h-full bg-green-500 transition-all"
          style={{ width: `${completedPct}%` }}
        />
        <div
          className="h-full bg-red-400 transition-all"
          style={{ width: `${failedPct}%` }}
        />
      </div>
      {failed > 0 && (
        <p className="text-xs text-red-500 mt-1">{failed} failed</p>
      )}
    </div>
  );
}
