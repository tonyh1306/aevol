"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { FlaskConical, Database, Cpu, FileBarChart } from "lucide-react";

const nav = [
  { href: "/experiments", label: "Experiments", icon: FlaskConical },
  { href: "/datasets", label: "Datasets", icon: Database },
  { href: "/workers", label: "Workers", icon: Cpu },
  { href: "/reports", label: "Reports", icon: FileBarChart },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-56 bg-gray-900 text-gray-100 flex flex-col">
      <div className="px-4 py-5 border-b border-gray-700">
        <span className="text-sm font-bold tracking-wide text-blue-400">EvalPlatform</span>
      </div>
      <nav className="flex-1 py-4 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-4 py-2 text-sm rounded-md mx-2 transition-colors",
              path.startsWith(href)
                ? "bg-blue-600 text-white"
                : "text-gray-300 hover:bg-gray-700"
            )}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
