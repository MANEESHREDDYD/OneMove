import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { Button } from "@/components/ui/button"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, MapPin, Package, Clock, DollarSign, Activity } from "lucide-react"
import { AdminOrderActions } from "./AdminOrderActions"

export default async function AdminOrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }

  const resolvedParams = await params

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) {
    redirect('/auth/login')
  }

  // Fetch admin role
  const { data: profile } = await supabase.from('profiles').select('role').eq('id', user.id).single()
  if (!profile || profile.role !== 'admin') {
    redirect('/auth/login')
  }

  // Fetch order with all relations
  const { data: order, error } = await supabase
    .from('orders')
    .select(`
      *,
      order_items (
        id, quantity, price_at_time,
        products ( name )
      ),
      payments ( amount, method, status )
    `)
    .eq('id', resolvedParams.id)
    .single()

  if (error || !order) {
    console.error("ADMIN ORDER PAGE LOAD ERROR:", { error, resolvedParamsId: resolvedParams.id, orderFound: !!order });
    return (
      <div className="space-y-8 animate-in fade-in">
        <PageHeader title="Order Not Found" description="The requested record could not be loaded." />
        <Link href="/admin/command-center">
          <Button variant="outline"><ArrowLeft className="w-4 h-4 mr-2" /> Back</Button>
        </Link>
      </div>
    )
  }

  const items = order.order_items || []
  const payments = order.payments || []

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title={`Order Details`} 
          description={`ID: ${order.id}`}
        />
        <Link href="/admin/command-center">
          <Button variant="ghost" className="rounded-full text-xs">
            <ArrowLeft className="w-3 h-3 mr-1" /> Back
          </Button>
        </Link>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <GlassCard className="p-6 space-y-4">
            <h3 className="font-bold flex items-center gap-2"><Package className="w-5 h-5 text-primary" /> Order Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground uppercase">Service Type</p>
                <p className="font-medium capitalize">{order.service_type}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">Current Status</p>
                <p className="font-bold text-primary uppercase">{order.status.replace('_', ' ')}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">Customer ID</p>
                <p className="text-sm font-mono truncate">{order.customer_id || 'N/A'}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase">Partner/Driver ID</p>
                <p className="text-sm font-mono truncate">{order.driver_id || 'Unassigned'}</p>
              </div>
              {order.merchant_id && (
                <div className="col-span-2">
                  <p className="text-xs text-muted-foreground uppercase">Merchant ID</p>
                  <p className="text-sm font-mono truncate">{order.merchant_id}</p>
                </div>
              )}
            </div>
          </GlassCard>

          {['eats', 'grocery'].includes(order.service_type) && items.length > 0 && (
            <GlassCard className="p-6">
              <h3 className="font-bold flex items-center gap-2 mb-4"><Package className="w-5 h-5 text-primary" /> Items</h3>
              <div className="space-y-2">
                {items.map((item: any) => (
                  <div key={item.id} className="flex justify-between items-center bg-background/50 p-2 rounded-lg text-sm">
                    <span><span className="font-bold mr-2">{item.quantity}x</span> {item.products?.name || 'Unknown'}</span>
                    <span className="text-muted-foreground">${((item.price_at_time || 0) * (item.quantity || 1)).toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          {order.service_type === 'ride' && (
            <GlassCard className="p-6 space-y-4">
              <h3 className="font-bold flex items-center gap-2"><MapPin className="w-5 h-5 text-blue-500" /> Route Details</h3>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="mt-1 bg-blue-500/20 p-1.5 rounded-full"><MapPin className="w-4 h-4 text-blue-500" /></div>
                  <div>
                    <p className="text-xs font-bold text-muted-foreground uppercase">Pickup</p>
                    <p className="text-sm">{(order.pickup_location as any)?.address || 'N/A'}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="mt-1 bg-destructive/20 p-1.5 rounded-full"><MapPin className="w-4 h-4 text-destructive" /></div>
                  <div>
                    <p className="text-xs font-bold text-muted-foreground uppercase">Dropoff</p>
                    <p className="text-sm">{(order.dropoff_location as any)?.address || 'N/A'}</p>
                  </div>
                </div>
              </div>
            </GlassCard>
          )}

        </div>

        <div className="space-y-6">
          <GlassCard className="p-6 border-t-4 border-t-green-500">
            <h3 className="font-bold flex items-center gap-2 mb-4"><DollarSign className="w-5 h-5 text-green-500" /> Payment & Totals</h3>
            <div className="text-3xl font-black mb-4">${order.total_amount?.toFixed(2)}</div>
            {payments.map((p: any, idx: number) => (
              <div key={idx} className="bg-background/50 p-3 rounded-lg text-sm space-y-1 mb-2">
                <div className="flex justify-between"><span className="text-muted-foreground">Method:</span> <span className="capitalize">{p.method.replace('_', ' ')}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Status:</span> <span className="font-bold">{p.status.replace('_', ' ')}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Amount:</span> <span>${p.amount.toFixed(2)}</span></div>
              </div>
            ))}
            {payments.length === 0 && <p className="text-sm text-muted-foreground italic">No payment records found.</p>}
          </GlassCard>

          <GlassCard className="p-6">
            <h3 className="font-bold flex items-center gap-2 mb-4"><Activity className="w-5 h-5 text-purple-500" /> Admin Actions</h3>
            <AdminOrderActions orderId={order.id} currentStatus={order.status} serviceType={order.service_type} />
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
