"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Boxes,
  Cpu,
  Database,
  FileSearch,
  FlaskConical,
  History,
  Layers,
  LayoutDashboard,
  MessageSquare,
  ShieldAlert,
} from "lucide-react";
import { useAuth } from "./auth/auth-provider";

interface NavItem {
  name: string;
  href: string;
  icon: typeof LayoutDashboard;
}

const NAV_ITEMS: NavItem[] = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Network", href: "/network", icon: Layers },
  { name: "Data Health", href: "/data-health", icon: Database },
  { name: "System Health", href: "/system-health", icon: Activity },
  { name: "Optimize", href: "/optimize", icon: Cpu },
  { name: "Resilience", href: "/resilience", icon: ShieldAlert },
  { name: "Scenarios", href: "/scenarios", icon: Boxes },
  { name: "Experiments", href: "/experiments", icon: FlaskConical },
  { name: "Decisions", href: "/decisions", icon: History },
  { name: "Time Travel", href: "/replay", icon: History },
  { name: "Evidence", href: "/evidence", icon: FileSearch },
  { name: "Assistant", href: "/assistant", icon: MessageSquare },
];

export function NavigationHeader() {
  const pathname = usePathname();
  const { workspaceId, role } = useAuth();

  return (
    <header className="border-b border-slate-200 bg-white shadow-sm" role="banner">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="flex items-center gap-2 font-bold text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-black text-sm">
                ZP
              </div>
              <span className="text-lg tracking-tight">ZonePilot Observatory</span>
            </Link>
            {workspaceId && (
              <span className="hidden sm:inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                {workspaceId} ({role})
              </span>
            )}
          </div>

          <nav
            aria-label="Main Navigation"
            className="flex items-center gap-1 overflow-x-auto py-2 scrollbar-none"
          >
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 py-1.5 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${
                    isActive
                      ? "bg-blue-50 text-blue-700"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                  aria-current={isActive ? "page" : undefined}
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
