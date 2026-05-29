import { PageHeader } from "@/components/common/PageHeader"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { AdminDashboardClient } from "./AdminDashboardClient"

export default async function AdminCommandCenter() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // Admin God Mode: Fetch ALL orders across the entire platform
  const { data: ordersData } = await supabase
    .from('orders')
    .select('*')
    .order('created_at', { ascending: false })

  const globalOrders = ordersData || []

  // Platform Metrics Calculation
  const totalOrders = globalOrders.length
  
  // Calculate GMV (Gross Merchandise Value)
  const gmv = globalOrders.reduce((sum, order) => sum + (order.total_amount || 0), 0)

  // Calculate unique active customers
  const uniqueCustomers = new Set(globalOrders.map(order => order.customer_id))
  const activeCustomers = uniqueCustomers.size

  // Calculate completion rate
  const completedOrders = globalOrders.filter(o => o.status === 'completed').length
  const completionRate = totalOrders > 0 ? (completedOrders / totalOrders) * 100 : 0

  const metrics = {
    gmv,
    totalOrders,
    activeCustomers,
    completionRate
  }

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Command Center" 
          description="Platform-wide God Mode"
        />
        <form action={signout}>
          <Button variant="ghost" className="rounded-full text-xs">Sign Out</Button>
        </form>
      </div>

      <AdminDashboardClient 
        globalOrders={globalOrders}
        metrics={metrics}
      />
    </div>
  )
}
