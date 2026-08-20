"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Car, Utensils, ShoppingBag, Package, LayoutDashboard, Settings, Map, LineChart, Shield, LifeBuoy, Brain, Headphones, Beaker, Activity } from "lucide-react"
import { MAIN_CONTENT_ID } from "@/lib/a11y"

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

type NavSection = {
  items: typeof CUSTOMER_NAV
  /**
   * Names the navigation landmark. Two <nav> elements are rendered (desktop
   * sidebar + mobile bottom bar); a screen-reader user listing landmarks needs
   * to be able to tell them apart, so each gets a distinct accessible name
   * built from this label.
   */
  label: string
}

/**
 * OneMove operator navigation.
 *
 * /network and /executive are decision-platform routes, but they fell through to
 * CUSTOMER_NAV, so the network view was framed by Rides / Eats / Grocery /
 * Courier -- presenting a network-optimisation product as a delivery marketplace.
 * Only routes that actually exist are listed here.
 */
const OPERATOR_NAV = [
  { name: "Overview", href: "/executive", icon: LayoutDashboard },
  { name: "Network", href: "/network", icon: Map },
  { name: "Command Center", href: "/admin/command-center", icon: LineChart },
  { name: "System Health", href: "/admin/system-health", icon: Shield },
]

const OPERATOR_PREFIXES = ["/network", "/executive"]

function getNavSection(pathname: string): NavSection {
  if (OPERATOR_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(prefix + "/"))) {
    return { items: OPERATOR_NAV, label: "Operator" }
  }
  if (pathname.startsWith("/admin")) return { items: ADMIN_NAV, label: "Admin" }
  if (pathname.startsWith("/partner")) return { items: DRIVER_NAV, label: "Partner" }
  if (pathname.startsWith("/merchant")) return { items: MERCHANT_NAV, label: "Merchant" }
  return { items: CUSTOMER_NAV, label: "Customer" }
}

function isItemActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(href + "/")
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  // The landing page renders its own <header>/<main>/<footer>, including the
  // single #main-content landmark. Wrapping it here would nest those landmarks
  // inside <main> and strip them of their banner / contentinfo roles.
  if (pathname === "/") {
    return <>{children}</>
  }

  // Auth routes get no navigation chrome, but still need exactly one <main>
  // landmark so the skip link in the root layout has a target.
  if (pathname.startsWith("/auth")) {
    return (
      <main id={MAIN_CONTENT_ID} tabIndex={-1}>
        {children}
      </main>
    )
  }

  const { items: navItems, label: navLabel } = getNavSection(pathname)

  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex w-64 flex-col border-r border-border bg-card/50 backdrop-blur-sm fixed inset-y-0 z-50">
        <div className="p-6">
          <Link href="/" className="text-2xl font-bold tracking-tight">OneMove</Link>
        </div>
        <nav aria-label={`${navLabel} sections`} className="flex-1 px-4 space-y-2">
          {navItems.map((item) => {
            const isActive = isItemActive(pathname, item.href)
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                href={item.href}
                // aria-current is what actually tells a screen reader which
                // entry is the current page. The colour swap below is a
                // supplement to it, never the sole signal.
                aria-current={isActive ? "page" : undefined}
                className={`relative flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground font-semibold"
                    : "hover:bg-white/10 text-muted-foreground hover:text-foreground"
                }`}
              >
                {/*
                  Non-colour indicator for the active entry: a solid bar on the
                  leading edge, so the current page is still identifiable
                  without perceiving the background/foreground colour change
                  (WCAG 1.4.1 Use of Color). Decorative — the name is carried by
                  aria-current.
                */}
                {isActive && (
                  <span
                    aria-hidden="true"
                    className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-primary-foreground"
                  />
                )}
                <Icon aria-hidden="true" focusable="false" className="w-5 h-5" />
                <span className="font-medium">{item.name}</span>
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main
        id={MAIN_CONTENT_ID}
        // Focusable only programmatically, so the skip link can move focus here
        // rather than merely moving the scroll position.
        tabIndex={-1}
        className="min-w-0 flex-1 pb-20 md:pl-64 md:pb-0"
      >
        <div className="p-4 md:p-8 max-w-7xl mx-auto">
          {children}
        </div>
      </main>

      {/* Mobile Bottom Nav */}
      <nav
        aria-label={`${navLabel} sections, compact`}
        className="md:hidden fixed bottom-0 inset-x-0 border-t border-border bg-card/80 backdrop-blur-lg z-50 pb-safe"
      >
        <div className="flex items-center justify-around p-2">
          {navItems.slice(0, 5).map((item) => {
            const isActive = isItemActive(pathname, item.href)
            const Icon = item.icon
            return (
              <Link
                key={item.name}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={`relative flex flex-col items-center p-2 rounded-lg transition-colors ${
                  isActive
                    ? "text-primary font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {/* Non-colour active indicator: see the sidebar comment above. */}
                {isActive && (
                  <span
                    aria-hidden="true"
                    className="absolute top-0 h-0.5 w-8 rounded-full bg-primary"
                  />
                )}
                <Icon aria-hidden="true" focusable="false" className="w-6 h-6 mb-1" />
                <span className="text-[10px] font-medium">{item.name}</span>
              </Link>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
