import { PageHeader } from "@/components/common/PageHeader"
import { SetupRequired } from "@/components/common/SetupRequired"
import { SignOutButton } from "@/components/auth/SignOutButton"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import Link from "next/link"
import { AdminDashboardClient } from "./AdminDashboardClient"

export default async function AdminCommandCenter() {
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

  if (profile?.role !== 'admin') {
    redirect(`/${profile?.role || 'customer'}`)
  }

  // Admin God Mode: Fetch metrics via optimized RPC
  const { data: rpcData } = await supabase.rpc('get_admin_dashboard_metrics')
  const dashboardMetrics = rpcData as {
    summary?: {
      pending_orders?: number
      active_orders?: number
      completed_orders?: number
      total_customers?: number
    }
  } | null

  // Fetch only recent orders for the feed and map
  const { data: ordersData } = await supabase
    .from('orders')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(50)

  const { data: merchantsData } = await supabase
    .from('merchants')
    .select('*')

  const globalOrders = ordersData || []
  const merchants = merchantsData || []

  // Platform Metrics Calculation
  const totalOrders = (dashboardMetrics?.summary?.pending_orders ?? 0) + (dashboardMetrics?.summary?.active_orders ?? 0) + (dashboardMetrics?.summary?.completed_orders ?? 0)
  const activeCustomers = dashboardMetrics?.summary?.total_customers || 0
  const completedOrders = dashboardMetrics?.summary?.completed_orders || 0
  const completionRate = totalOrders > 0 ? (completedOrders / totalOrders) * 100 : 0
  
  // Estimate GMV roughly based on recent orders if not tracked strictly in RPC,
  // or we can just fetch a quick sum if needed. We'll use the recent feed for now 
  // or just hardcode a placeholder if true GMV calculation needs a separate query.
  // Actually, let's just sum the recent orders to show "Recent GMV" to save performance
  const gmv = globalOrders.reduce((sum, order) => sum + (order.total_amount || 0), 0)

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
        <div className="flex items-center gap-4">
          <Link href="/admin/compliance">
            <Button variant="outline" className="rounded-full text-xs font-bold border-destructive text-destructive hover:bg-destructive/10">
              Safety & Compliance
            </Button>
          </Link>
          <Link href="/admin/ml-lab">
            <Button variant="outline" className="rounded-full text-xs font-bold border-purple-500 text-purple-500 hover:bg-purple-500/10">
              ML Lab
            </Button>
          </Link>
          <Link href="/admin/analytics">
            <Button variant="outline" className="rounded-full text-xs font-bold border-primary text-primary hover:bg-primary/10">
              View Analytics
            </Button>
          </Link>
          <SignOutButton className="rounded-full text-xs" />
        </div>
      </div>

      <AdminDashboardClient 
        globalOrders={globalOrders}
        merchants={merchants}
        metrics={metrics}
      />
    </div>
  )
}
