import { PageHeader } from "@/components/common/PageHeader"
import { SetupRequired } from "@/components/common/SetupRequired"
import { Button } from "@/components/ui/button"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { AnalyticsClient } from "./AnalyticsClient"

export default async function AnalyticsPage() {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // Fetch ALL orders
  const { data: ordersData } = await supabase
    .from('orders')
    .select('*')

  const globalOrders = ordersData || []

  // Initialize aggregators
  const revenueMap: Record<string, number> = { ride: 0, eats: 0, grocery: 0, courier: 0 }
  const volumeMap: Record<string, number> = { ride: 0, eats: 0, grocery: 0, courier: 0 }

  // Aggregate data
  globalOrders.forEach(order => {
    const type = order.service_type
    if (revenueMap[type] !== undefined) {
      // Only count revenue for completed orders? For MVP, we'll count all valid amounts
      revenueMap[type] += (order.total_amount || 0)
      volumeMap[type] += 1
    }
  })

  // Format for Recharts
  const revenueData = Object.keys(revenueMap).map(key => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    revenue: Number(revenueMap[key].toFixed(2))
  }))

  const volumeData = Object.keys(volumeMap).map(key => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    value: volumeMap[key]
  }))

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Analytics Dashboard" 
          description="Business intelligence & data visualization"
        />
        <Link href="/admin/command-center">
          <Button variant="ghost" className="rounded-full text-xs">
            <ArrowLeft className="w-3 h-3 mr-1" /> Back to Command Center
          </Button>
        </Link>
      </div>

      <AnalyticsClient 
        revenueData={revenueData}
        volumeData={volumeData}
      />
    </div>
  )
}
