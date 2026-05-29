import Link from "next/link"
import { buttonVariants } from "@/components/ui/button"
import { Car, Utensils, ShoppingBag, Package, Tag, ShieldCheck, Map, Activity } from "lucide-react"
import { GlassCard } from "@/components/common/GlassCard"
import { ServiceCard } from "@/components/common/ServiceCard"

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="fixed top-0 inset-x-0 h-16 bg-background/80 backdrop-blur-md border-b z-50 flex items-center justify-between px-6">
        <div className="text-2xl font-bold tracking-tight">OneMove</div>
        <div className="flex gap-4">
          <Link href="/auth/login" className={buttonVariants({ variant: "ghost" })}>
            Login
          </Link>
          <Link href="/auth/register" className={buttonVariants()}>
            Get Started
          </Link>
        </div>
      </header>

      <main className="flex-1 pt-16">
        {/* Hero Section */}
        <section className="py-20 px-6 text-center max-w-4xl mx-auto space-y-8">
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-br from-white to-white/50">
            One city app for rides, food, groceries, and local delivery.
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            A US-first, global-ready PWA super-app with marketplace intelligence, transparent pricing, and city-level operations.
          </p>
          <div className="flex items-center justify-center gap-4 pt-4">
            <Link href="/customer" className={buttonVariants({ size: "lg", className: "rounded-full px-8" })}>
              Start Demo
            </Link>
            <Link href="/admin/command-center" className={buttonVariants({ size: "lg", variant: "outline", className: "rounded-full px-8" })}>
              View Command Center
            </Link>
          </div>
        </section>

        {/* Service Grid */}
        <section className="py-16 px-6 max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <ServiceCard title="Ride" icon={Car} href="/customer/rides" />
            <ServiceCard title="Eats" icon={Utensils} href="/customer/eats" />
            <ServiceCard title="Grocery" icon={ShoppingBag} href="/customer/grocery" />
            <ServiceCard title="Courier" icon={Package} href="/customer/courier" />
            <ServiceCard title="Local Deals" icon={Tag} href="/customer" />
          </div>
        </section>

        {/* Live City Preview */}
        <section className="py-16 px-6 max-w-6xl mx-auto">
          <GlassCard className="p-8 flex flex-col md:flex-row gap-8 items-center border-primary/20">
            <div className="flex-1 space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 text-primary text-sm font-medium">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                </span>
                Live in NYC
              </div>
              <h2 className="text-3xl font-bold">City Command Center</h2>
              <p className="text-muted-foreground">
                Simulated city map with moving driver markers, active order markers, and real-time demand zones.
              </p>
            </div>
            <div className="flex-1 w-full aspect-video bg-muted rounded-xl flex items-center justify-center border">
              <Map className="w-12 h-12 text-muted-foreground/50" />
              <span className="ml-2 text-muted-foreground font-medium">Map Preview</span>
            </div>
          </GlassCard>
        </section>

        {/* Features Grid */}
        <section className="py-16 px-6 max-w-6xl mx-auto grid md:grid-cols-2 gap-6">
          <GlassCard className="p-8 space-y-4">
            <ShieldCheck className="w-10 h-10 text-green-500" />
            <h3 className="text-xl font-bold">Trust & Safety</h3>
            <p className="text-muted-foreground">SOS features, live tracking, verified partners, and transparent upfront pricing.</p>
          </GlassCard>

          <GlassCard className="p-8 space-y-4">
            <Car className="w-10 h-10 text-blue-500" />
            <h3 className="text-xl font-bold">Driver-first Platform</h3>
            <p className="text-muted-foreground">Clear earnings breakdown, 100% tips to drivers, live demand zones, and trust scores.</p>
          </GlassCard>

          <GlassCard className="p-8 space-y-4">
            <ShoppingBag className="w-10 h-10 text-orange-500" />
            <h3 className="text-xl font-bold">Merchant Platform</h3>
            <p className="text-muted-foreground">Free storefront setup, menu and inventory management, order processing, and rich analytics.</p>
          </GlassCard>

          <GlassCard className="p-8 space-y-4">
            <Activity className="w-10 h-10 text-purple-500" />
            <h3 className="text-xl font-bold">Data & AI Showcase</h3>
            <p className="text-muted-foreground">Advanced data platform, ML lab scoring, dispatch intelligence, and predictive ETA.</p>
          </GlassCard>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t py-8 text-center text-sm text-muted-foreground">
        <p>OneMove MVP - A Zero-Cost Demo Platform</p>
      </footer>
    </div>
  )
}
