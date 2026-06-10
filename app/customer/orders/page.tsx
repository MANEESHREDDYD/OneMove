import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import Link from "next/link"
import { StatusBadge } from "@/components/common/StatusBadge"
import { Car, ShoppingBag, ShoppingBasket, Package, TrendingUp } from "lucide-react"

export const dynamic = "force-dynamic"

export default async function CustomerOrders() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: orders } = await supabase
    .from('orders')
    .select('*, merchants(name)')
    .eq('customer_id', user.id)
    .order('created_at', { ascending: false })

  const allOrders = orders || []

  // Active vs Past
  const activeStatuses = ['pending', 'accepted', 'preparing', 'ready', 'in_transit']
  const activeOrders = allOrders.filter(o => activeStatuses.includes(o.status))
  const pastOrders = allOrders.filter(o => !activeStatuses.includes(o.status))

  const rides = pastOrders.filter(o => o.service_type === 'ride')
  const food = pastOrders.filter(o => o.service_type === 'eats')
  const grocery = pastOrders.filter(o => o.service_type === 'grocery')
  const courier = pastOrders.filter(o => o.service_type === 'courier')

  // Monthly Spending
  const thirtyDaysAgo = new Date()
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
  
  const recentOrders = allOrders.filter(o => new Date(o.created_at) >= thirtyDaysAgo && o.status !== 'cancelled')
  
  const totalSpent = recentOrders.reduce((sum, o) => sum + (o.total_amount || 0), 0)
  const ridesSpent = recentOrders.filter(o => o.service_type === 'ride').reduce((sum, o) => sum + (o.total_amount || 0), 0)
  const eatsSpent = recentOrders.filter(o => o.service_type === 'eats').reduce((sum, o) => sum + (o.total_amount || 0), 0)
  const grocSpent = recentOrders.filter(o => o.service_type === 'grocery').reduce((sum, o) => sum + (o.total_amount || 0), 0)
  const courSpent = recentOrders.filter(o => o.service_type === 'courier').reduce((sum, o) => sum + (o.total_amount || 0), 0)
  
  const avgOrderValue = recentOrders.length > 0 ? totalSpent / recentOrders.length : 0

  const OrderCard = ({ order }: { order: { id: string; merchants?: { name?: string } | null; service_type: string; created_at: string; status: string; total_amount?: number } }) => (
    <Link href={`/customer/orders/${order.id}`}>
      <GlassCard className="p-4 flex flex-col md:flex-row md:items-center justify-between hover:bg-white/5 transition-colors group">
        <div>
          <h3 className="font-bold text-base capitalize">
            {order.merchants?.name || `${order.service_type} Service`}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {new Date(order.created_at).toLocaleDateString()} • {order.status === 'completed' ? 'Completed' : 'Ordered'}
          </p>
        </div>
        <div className="mt-4 md:mt-0 flex items-center gap-4">
          <span className="font-bold text-lg">${(order.total_amount || 0).toFixed(2)}</span>
          <StatusBadge status={order.status} />
          <span className="text-primary group-hover:underline text-sm font-medium">View details &rarr;</span>
        </div>
      </GlassCard>
    </Link>
  )

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
      <PageHeader title="Your History" description="Unified spending and order tracking" />

      {/* Monthly Spending */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <GlassCard className="p-4 col-span-2 md:col-span-4 bg-primary/5 border-primary/20 flex flex-col md:flex-row justify-between items-center">
          <div>
            <p className="text-sm text-muted-foreground font-semibold uppercase tracking-wider">30-Day Spending</p>
            <p className="text-4xl font-black">${totalSpent.toFixed(2)}</p>
          </div>
          <div className="mt-4 md:mt-0 flex gap-6 text-sm text-muted-foreground">
            <div>
              <p>Orders</p>
              <p className="font-bold text-foreground text-lg">{recentOrders.length}</p>
            </div>
            <div>
              <p>Rides</p>
              <p className="font-bold text-foreground text-lg">{recentOrders.filter(o => o.service_type === 'ride').length}</p>
            </div>
            <div>
              <p>Avg Value</p>
              <p className="font-bold text-foreground text-lg">${avgOrderValue.toFixed(2)}</p>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-4 space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground mb-2"><Car className="w-4 h-4"/> Rides</div>
          <p className="text-xl font-bold">${ridesSpent.toFixed(2)}</p>
        </GlassCard>
        <GlassCard className="p-4 space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground mb-2"><ShoppingBag className="w-4 h-4"/> Eats</div>
          <p className="text-xl font-bold">${eatsSpent.toFixed(2)}</p>
        </GlassCard>
        <GlassCard className="p-4 space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground mb-2"><ShoppingBasket className="w-4 h-4"/> Grocery</div>
          <p className="text-xl font-bold">${grocSpent.toFixed(2)}</p>
        </GlassCard>
        <GlassCard className="p-4 space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground mb-2"><Package className="w-4 h-4"/> Courier</div>
          <p className="text-xl font-bold">${courSpent.toFixed(2)}</p>
        </GlassCard>
      </div>

      {activeOrders.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold flex items-center gap-2 text-green-500"><TrendingUp className="w-5 h-5"/> Active Orders</h2>
          <div className="space-y-3">{activeOrders.map(o => <OrderCard key={o.id} order={o} />)}</div>
        </div>
      )}

      {food.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold flex items-center gap-2"><ShoppingBag className="w-5 h-5"/> Food Orders</h2>
          <div className="space-y-3">{food.slice(0, 5).map(o => <OrderCard key={o.id} order={o} />)}</div>
        </div>
      )}

      {grocery.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold flex items-center gap-2"><ShoppingBasket className="w-5 h-5"/> Grocery Orders</h2>
          <div className="space-y-3">{grocery.slice(0, 5).map(o => <OrderCard key={o.id} order={o} />)}</div>
        </div>
      )}

      {rides.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold flex items-center gap-2"><Car className="w-5 h-5"/> Ride History</h2>
          <div className="space-y-3">{rides.slice(0, 5).map(o => <OrderCard key={o.id} order={o} />)}</div>
        </div>
      )}

      {courier.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold flex items-center gap-2"><Package className="w-5 h-5"/> Courier Jobs</h2>
          <div className="space-y-3">{courier.slice(0, 5).map(o => <OrderCard key={o.id} order={o} />)}</div>
        </div>
      )}
    </div>
  )
}
