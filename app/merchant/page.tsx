import { PageHeader } from "@/components/common/PageHeader"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { MerchantDashboardClient } from "./MerchantDashboardClient"

export default async function MerchantDashboard() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // Fetch all relevant orders for MVP (eats & grocery)
  const { data: ordersData } = await supabase
    .from('orders')
    .select('*')
    .in('service_type', ['eats', 'grocery'])
    .order('created_at', { ascending: false })

  const allOrders = ordersData || []

  // Split into active and history
  const activeOrders = allOrders.filter(o => ['pending', 'accepted', 'preparing', 'ready', 'in_transit'].includes(o.status))
  // For history, we'll take completed or cancelled
  const historyOrders = allOrders.filter(o => ['completed', 'cancelled'].includes(o.status))

  // Calculate some MVP metrics based on today's orders (mocked to just all completed for now)
  const completedOrders = historyOrders.filter(o => o.status === 'completed')
  const totalRevenue = completedOrders.reduce((sum, o) => sum + (o.total_amount || 0), 0)
  const totalOrdersCount = allOrders.length

  const metrics = {
    totalRevenue,
    totalOrders: totalOrdersCount,
    completedOrders: completedOrders.length
  }

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Merchant Portal" 
          description="Manage your store and incoming orders"
        />
        <form action={signout}>
          <Button variant="ghost" className="rounded-full text-xs">Sign Out</Button>
        </form>
      </div>

      <MerchantDashboardClient 
        activeOrders={activeOrders.reverse()} // Oldest first for the active queue
        historyOrders={historyOrders} 
        metrics={metrics} 
      />
    </div>
  )
}
