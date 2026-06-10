import { PageHeader } from "@/components/common/PageHeader"
import { ServiceCard } from "@/components/common/ServiceCard"
import { GlassCard } from "@/components/common/GlassCard"
import { FloatingSOSButton } from "@/components/common/FloatingSOSButton"
import { SignOutButton } from "@/components/auth/SignOutButton"
import { SetupRequired } from "@/components/common/SetupRequired"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"
import { createClient } from "@/utils/supabase/server"
import { Car, Utensils, ShoppingBasket, Package, MapPin } from "lucide-react"
import Link from "next/link"
import { Database } from "@/types/database.types"

type Order = Database['public']['Tables']['orders']['Row']

export default async function CustomerDashboard() {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }
  const { data: { user } } = await supabase.auth.getUser()
  
  let activeOrders: Order[] = []
  if (user) {
    const { data } = await supabase
      .from('orders')
      .select('*')
      .eq('customer_id', user.id)
      .in('status', ['pending', 'placed', 'merchant_accepted', 'accepted', 'preparing', 'ready', 'in_transit'])
      .order('created_at', { ascending: false })
      .limit(3)
    activeOrders = data || []
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Good Morning" 
          description="Where to next?"
        />
        <SignOutButton className="rounded-full" />
      </div>
      
      {/* Active Orders Widget */}
      {activeOrders.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold tracking-tight">Active Orders</h2>
            <Link href="/customer/orders" className="text-sm text-primary hover:underline font-medium">View all</Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {activeOrders.map((order) => (
              <Link key={order.id} href={`/customer/orders/${order.id}`} className="block group">
                <GlassCard className="p-4 flex items-center gap-4 hover:bg-white/5 transition-colors cursor-pointer border border-primary/20">
                  <div className="bg-primary/20 p-3 rounded-full group-hover:scale-110 transition-transform">
                    {order.service_type === 'ride' && <Car className="h-6 w-6 text-primary" />}
                    {order.service_type === 'eats' && <Utensils className="h-6 w-6 text-primary" />}
                    {order.service_type === 'grocery' && <ShoppingBasket className="h-6 w-6 text-primary" />}
                    {order.service_type === 'courier' && <Package className="h-6 w-6 text-primary" />}
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <h3 className="font-semibold capitalize text-sm">{order.service_type} • {order.status.replace('_', ' ')}</h3>
                    <div className="flex items-center text-xs text-muted-foreground mt-1 gap-1">
                      <MapPin className="h-3 w-3" />
                      <span className="truncate max-w-[150px]">{(order.dropoff_location as { address?: string })?.address || 'In transit'}</span>
                    </div>
                  </div>
                </GlassCard>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Services Grid */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold tracking-tight">Services</h2>
        <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
          <ServiceCard
            title="Rides"
            description="Get there fast"
            icon={<Car className="h-6 w-6" />}
            href="/customer/rides"
            gradient="from-blue-500/20 to-cyan-500/20"
          />
          <ServiceCard
            title="Food"
            description="Cravings delivered"
            icon={<Utensils className="h-6 w-6" />}
            href="/customer/eats"
            gradient="from-orange-500/20 to-red-500/20"
          />
          <ServiceCard
            title="Grocery"
            description="Fresh & fast"
            icon={<ShoppingBasket className="h-6 w-6" />}
            href="/customer/grocery"
            gradient="from-green-500/20 to-emerald-500/20"
          />
          <ServiceCard
            title="Courier"
            description="Send packages"
            icon={<Package className="h-6 w-6" />}
            href="/customer/orders"
            gradient="from-purple-500/20 to-pink-500/20"
          />
        </div>
      </div>

      {/* Promotional / Banner */}
      <GlassCard className="p-6 relative overflow-hidden group mt-6">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/20 via-transparent to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-500" />
        <div className="relative z-10">
          <h3 className="text-xl font-bold tracking-tight mb-2">Try OneMove Prime</h3>
          <p className="text-muted-foreground mb-4 max-w-sm">Get $0 delivery fees on eligible food and grocery orders, plus 5% off rides.</p>
          <Button>Start Free Trial</Button>
        </div>
      </GlassCard>
      
      <FloatingSOSButton />
    </div>
  )
}
