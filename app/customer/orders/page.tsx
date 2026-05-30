import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import Link from "next/link"
import { StatusBadge } from "@/components/common/StatusBadge"

export default async function CustomerOrders() {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }

  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const { data: orders } = await supabase
    .from('orders')
    .select('*')
    .eq('customer_id', user.id)
    .order('created_at', { ascending: false })

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Your Orders" 
        description="Track your active orders and view past history."
      />
      <div className="space-y-4">
        {orders && orders.length > 0 ? (
          orders.map((order) => (
            <Link key={order.id} href={`/customer/orders/${order.id}`}>
              <GlassCard className="p-4 flex flex-col md:flex-row md:items-center justify-between hover:bg-white/5 transition-colors group">
                <div>
                  <h3 className="font-semibold capitalize">{order.service_type} Order</h3>
                  <p className="text-sm text-muted-foreground">
                    {new Date(order.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="mt-4 md:mt-0 flex items-center gap-4">
                  <span className="font-medium">${(order.total_amount || 0).toFixed(2)}</span>
                  <StatusBadge status={order.status} />
                  <span className="text-primary group-hover:underline text-sm font-medium">View details &rarr;</span>
                </div>
              </GlassCard>
            </Link>
          ))
        ) : (
          <GlassCard className="p-8 text-center text-muted-foreground">
            No orders found.
          </GlassCard>
        )}
      </div>
    </div>
  )
}
