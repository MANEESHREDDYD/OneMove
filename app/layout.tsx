import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { AppShell } from "@/components/layout/AppShell"
import { Toaster } from "@/components/ui/sonner"

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

export const viewport: Viewport = {
  themeColor: "#050505",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark" style={{ colorScheme: "dark" }}>
      <body className={`${inter.className} bg-background text-foreground antialiased selection:bg-primary/30`}>
        <AppShell>
          {children}
        </AppShell>
        <Toaster />
      </body>
    </html>
  )
}
