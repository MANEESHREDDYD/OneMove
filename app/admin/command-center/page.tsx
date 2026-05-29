import { PageHeader } from "@/components/common/PageHeader"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import Link from "next/link"
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
        <div className="flex items-center gap-4">
          <Link href="/admin/compliance">
            <Button variant="outline" className="rounded-full text-xs font-bold border-destructive text-destructive hover:bg-destructive/10">
              Safety & Compliance
            </Button>
          </Link>
          <Link href="/admin/ai-lab">
            <Button variant="outline" className="rounded-full text-xs font-bold border-purple-500 text-purple-500 hover:bg-purple-500/10">
              ML / AI Lab
            </Button>
          </Link>
          <Link href="/admin/analytics">
            <Button variant="outline" className="rounded-full text-xs font-bold border-primary text-primary hover:bg-primary/10">
              View Analytics
            </Button>
          </Link>
          <form action={signout}>
            <Button variant="ghost" className="rounded-full text-xs">Sign Out</Button>
          </form>
        </div>
      </div>

      <AdminDashboardClient 
        globalOrders={globalOrders}
        metrics={metrics}
      />
    </div>
  )
}
