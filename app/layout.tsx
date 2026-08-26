import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { AppShell } from "@/components/layout/AppShell"
import { Toaster } from "@/components/ui/sonner"
import { MAIN_CONTENT_ID } from "@/lib/a11y"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "OneMove — Physical Commerce Network Intelligence & Decision Platform",
  description: "Enterprise spatial network intelligence, multi-scenario resilience evaluation, and auditable decision optimization platform.",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "OneMove",
  },
}

/**
 * `maximumScale: 1` / `userScalable: false` were previously set here. That
 * emits `maximum-scale=1, user-scalable=no`, which blocks pinch-zoom on every
 * page of the app — a WCAG 2.1 AA failure under SC 1.4.4 (Resize Text) and a
 * *critical* axe violation (`meta-viewport`) on every single route. Operators
 * reading dense health tables on a phone are exactly the people who need to
 * zoom. Do not reintroduce those two keys to stop iOS input-focus zoom; fix the
 * input font-size instead.
 */
export const viewport: Viewport = {
  themeColor: "#050505",
  width: "device-width",
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark" style={{ colorScheme: "dark" }}>
      <body className={`${inter.className} bg-background text-foreground antialiased selection:bg-primary/30`}>
        {/*
          First focusable element on every page. Lets a keyboard or switch user
          jump past the sidebar / bottom navigation, which is otherwise repeated
          on every route (WCAG 2.4.1 Bypass Blocks). Every route renders exactly
          one element with this id — see AppShell and app/page.tsx.
        */}
        <a href={`#${MAIN_CONTENT_ID}`} className="skip-to-main">
          Skip to main content
        </a>
        <AppShell>
          {children}
        </AppShell>
        <Toaster />
      </body>
    </html>
  )
}
