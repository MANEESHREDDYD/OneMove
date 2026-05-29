import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { Store, Clock, Utensils } from "lucide-react"
import { MerchantActionButtons } from "./MerchantActionButtons"

export default async function MerchantDashboard() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // Fetch orders for this merchant.
  // In a real app, we'd filter by merchant ID. For MVP, we'll fetch all `eats` and `grocery` orders 
  // that are not completed or cancelled, assuming the merchant is looking at their queue.
  const { data: ordersData } = await supabase
    .from('orders')
    .select('*')
    .in('service_type', ['eats', 'grocery'])
    .in('status', ['pending', 'accepted', 'preparing', 'ready'])
    .order('created_at', { ascending: true })

  const orders = ordersData || []

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Merchant Portal" 
          description="Manage your incoming orders"
        />
        <form action={signout}>
          <Button variant="ghost" className="rounded-full text-xs">Sign Out</Button>
        </form>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {orders.length === 0 ? (
          <GlassCard className="col-span-full p-12 text-center border-dashed border-primary/20">
            <Store className="h-12 w-12 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="font-semibold text-lg">No active orders</p>
            <p className="text-muted-foreground mt-1">Waiting for customers...</p>
          </GlassCard>
        ) : (
          orders.map((order) => {
            const items = (order.metadata as { items?: { name: string, quantity: number }[] })?.items || []
            
            return (
              <GlassCard key={order.id} className="p-5 flex flex-col justify-between h-full border-t-4 border-t-orange-500">
                <div>
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <p className="text-xs text-muted-foreground uppercase font-bold tracking-wider mb-1">
                        Order #{order.id.split('-')[0]}
                      </p>
                      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-bold bg-primary/10 text-primary">
                        <Clock className="w-3 h-3" />
                        {order.status.replace('_', ' ')}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-lg">${order.total_amount?.toFixed(2)}</p>
                    </div>
                  </div>

                  <div className="space-y-2 mb-4 bg-black/20 p-3 rounded-lg">
                    <h4 className="text-xs font-bold uppercase text-muted-foreground mb-2 flex items-center gap-1">
                      <Utensils className="w-3 h-3" /> Items to Prepare
                    </h4>
                    {items.map((item, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span className="font-medium"><span className="text-orange-500 mr-2">{item.quantity}x</span> {item.name}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <MerchantActionButtons orderId={order.id} currentStatus={order.status} />
              </GlassCard>
            )
          })
        )}
      </div>
    </div>
  )
}
