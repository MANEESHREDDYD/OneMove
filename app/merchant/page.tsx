import { PageHeader } from "@/components/common/PageHeader"
import { SignOutButton } from "@/components/auth/SignOutButton"
import { SetupRequired } from "@/components/common/SetupRequired"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { MerchantDashboardClient } from "./MerchantDashboardClient"
import { MerchantRealtime } from "@/components/realtime/MerchantRealtime"

export default async function MerchantDashboard() {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single()

  if (profile?.role !== 'merchant') {
    redirect(`/${profile?.role || 'customer'}`)
  }

  // Find the merchants owned by this user
  const { data: merchants } = await supabase
    .from('merchants')
    .select('id')
    .eq('owner_id', user.id)

  const merchantIds = merchants?.map(m => m.id) || []

  // If they have no merchants, they have no orders
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let ordersData: any[] = []
  
  if (merchantIds.length > 0) {
    const { data } = await supabase
      .from('orders')
      .select(`
        *,
        order_items(
          quantity,
          products(name)
        )
      `)
      .in('service_type', ['eats', 'grocery'])
      .in('merchant_id', merchantIds)
      .order('created_at', { ascending: false })
      .limit(50)
      
    ordersData = data || []
  }

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
      <MerchantRealtime merchantIds={merchantIds} />
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Merchant Portal" 
          description="Manage your store and incoming orders"
        />
        <SignOutButton className="rounded-full text-xs" />
      </div>

      <MerchantDashboardClient 
        activeOrders={activeOrders.reverse()} // Oldest first for the active queue
        historyOrders={historyOrders} 
        metrics={metrics} 
      />
    </div>
  )
}
