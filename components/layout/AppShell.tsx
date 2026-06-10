"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Car, Utensils, ShoppingBag, Package, LayoutDashboard, Settings, Map, LineChart, Shield, LifeBuoy, Brain, Headphones, Beaker, Activity } from "lucide-react"

const CUSTOMER_NAV = [
  { name: "Dashboard", href: "/customer", icon: LayoutDashboard },
  { name: "Rides", href: "/customer/rides", icon: Car },
  { name: "Eats", href: "/customer/eats", icon: Utensils },
  { name: "Grocery", href: "/customer/grocery", icon: ShoppingBag },
  { name: "Courier", href: "/customer/courier", icon: Package },
  { name: "Support", href: "/customer/support", icon: LifeBuoy },
  { name: "Profile", href: "/customer/profile", icon: Settings },
]

const DRIVER_NAV = [
  { name: "Dashboard", href: "/partner", icon: LayoutDashboard },
]

const MERCHANT_NAV = [
  { name: "Dashboard", href: "/merchant", icon: LayoutDashboard },
]

const ADMIN_NAV = [
  { name: "Command Center", href: "/admin/command-center", icon: LayoutDashboard },
  { name: "Analytics", href: "/admin/analytics", icon: LineChart },
  { name: "ML Lab", href: "/admin/ml-lab", icon: Map },
  { name: "Compliance", href: "/admin/compliance", icon: Shield },
  { name: "Ops Assistant", href: "/admin/ops-assistant", icon: Brain },
  { name: "Support Desk", href: "/admin/support-desk", icon: Headphones },
  { name: "Experiments", href: "/admin/experiments", icon: Beaker },
  { name: "MLOps", href: "/admin/mlops", icon: Activity },
]

function getNavItems(pathname: string) {
  if (pathname.startsWith("/admin")) return ADMIN_NAV
  if (pathname.startsWith("/partner")) return DRIVER_NAV
  if (pathname.startsWith("/merchant")) return MERCHANT_NAV
  return CUSTOMER_NAV
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  // For the landing page or auth pages, we might not want the shell
  const isPublicRoute = pathname === "/" || pathname.startsWith("/auth")
  if (isPublicRoute) {
    return <>{children}</>
  }

  const navItems = getNavItems(pathname)

  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-64 flex-col border-r border-border bg-card/50 backdrop-blur-sm fixed inset-y-0 z-50">
        <div className="p-6">
          <Link href="/" className="text-2xl font-bold tracking-tight">OneMove</Link>
        </div>
        <nav className="flex-1 px-4 space-y-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/")
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive 
                    ? "bg-primary text-primary-foreground" 
                    : "hover:bg-white/10 text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.name}</span>
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="min-w-0 flex-1 pb-20 md:pl-64 md:pb-0">
        <div className="p-4 md:p-8 max-w-7xl mx-auto">
          {children}
        </div>
      </main>

      {/* Mobile Bottom Nav */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 border-t border-border bg-card/80 backdrop-blur-lg z-50 pb-safe">
        <div className="flex items-center justify-around p-2">
          {navItems.slice(0, 5).map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/")
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex flex-col items-center p-2 rounded-lg transition-colors ${
                  isActive 
                    ? "text-primary" 
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className="w-6 h-6 mb-1" />
                <span className="text-[10px] font-medium">{item.name}</span>
              </Link>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
