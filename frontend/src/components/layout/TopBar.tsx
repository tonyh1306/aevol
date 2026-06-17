"use client";
import { usePathname } from "next/navigation";

const titles: Record<string, string> = {
  "/experiments": "Experiments",
  "/datasets": "Datasets",
  "/workers": "Workers",
  "/reports": "Reports",
};

export function TopBar() {
  const path = usePathname();
  const segments = path.split("/").filter(Boolean);
  const title = titles[`/${segments[0]}`] ?? "EvalPlatform";

  return (
    <header className="h-12 border-b border-gray-200 bg-white flex items-center px-6 gap-2">
      <span className="text-sm font-semibold text-gray-700">{title}</span>
    </header>
  );
}
