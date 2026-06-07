import { PageHeader } from "@/components/common/PageHeader"
import { SetupRequired } from "@/components/common/SetupRequired"
import { Button } from "@/components/ui/button"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { AnalyticsClient } from "./AnalyticsClient"
import { GlassCard } from "@/components/common/GlassCard"

export default async function AnalyticsPage() {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // Fetch 7-day trend from metric store
  const d = new Date()
  d.setDate(d.getDate() - 7)
  const lastWeek = d.toISOString().split('T')[0]

  const { data: globalMetrics } = await supabase
    .from('daily_marketplace_metrics')
    .select('*')
    .gte('date', lastWeek)
    .order('date', { ascending: true })

  const { data: serviceMetrics } = await supabase
    .from('service_type_daily_metrics')
    .select('*')
    .gte('date', lastWeek)

  // KPI calculations (latest date)
  const latestMetrics = globalMetrics && globalMetrics.length > 0 ? globalMetrics[globalMetrics.length - 1] : null

  // Prepare trend data for charts
  const trendData = (globalMetrics || []).map(m => ({
    date: m.date,
    gmv: Number(m.gmv),
    orders: Number(m.total_orders)
  }))

  // Prepare Service Type Distribution (summing last 7 days)
  const volumeMap: Record<string, number> = {}
  const revenueMap: Record<string, number> = {}
  
  if (serviceMetrics) {
    serviceMetrics.forEach(sm => {
      const type = sm.service_type
      volumeMap[type] = (volumeMap[type] || 0) + Number(sm.total_orders)
      revenueMap[type] = (revenueMap[type] || 0) + Number(sm.gmv)
    })
  }

  const volumeData = Object.keys(volumeMap).map(key => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    value: volumeMap[key]
  }))

  const revenueData = Object.keys(revenueMap).map(key => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    revenue: Number(revenueMap[key].toFixed(2))
  }))

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Analytics Dashboard" 
          description="Business intelligence powered by Metric Store"
        />
        <Link href="/admin/command-center">
          <Button variant="ghost" className="rounded-full text-xs">
            <ArrowLeft className="w-3 h-3 mr-1" /> Back to Command Center
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <GlassCard className="p-4 space-y-1">
          <p className="text-sm text-muted-foreground">Daily GMV</p>
          <p className="text-2xl font-bold">${latestMetrics?.gmv || 0}</p>
        </GlassCard>
        <GlassCard className="p-4 space-y-1">
          <p className="text-sm text-muted-foreground">Total Orders</p>
          <p className="text-2xl font-bold">{latestMetrics?.total_orders || 0}</p>
        </GlassCard>
        <GlassCard className="p-4 space-y-1">
          <p className="text-sm text-muted-foreground">Active Customers</p>
          <p className="text-2xl font-bold">{latestMetrics?.active_customers || 0}</p>
        </GlassCard>
        <GlassCard className="p-4 space-y-1">
          <p className="text-sm text-muted-foreground">Refund Rate</p>
          <p className="text-2xl font-bold">{latestMetrics?.refund_rate || 0}%</p>
        </GlassCard>
      </div>

      <AnalyticsClient 
        trendData={trendData}
        revenueData={revenueData}
        volumeData={volumeData}
      />
    </div>
  )
}
