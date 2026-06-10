import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { SetupRequired } from "@/components/common/SetupRequired"
import { GlassCard } from '@/components/common/GlassCard'
import { Car, Utensils, ShoppingBasket, Package, MapPin, Navigation, Clock, CheckCircle2, Receipt, ShieldAlert } from 'lucide-react'
import { CancelOrderButton } from './CancelOrderButton'
import { Button } from '@/components/ui/button'
import { SafeLeafletMap } from '@/components/maps/SafeLeafletMap'
import { AutoRefresh } from '@/components/common/AutoRefresh'

export const dynamic = "force-dynamic"

export default async function OrderTrackingPage({ params }: { params: Promise<{ id: string }> }) {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const resolvedParams = await params;

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: order, error } = await supabase
    .from('orders')
    .select(`
      *,
      merchants (name)
    `)
    .eq('id', resolvedParams.id)
    .single()

  if (error || !order || order.customer_id !== user.id) {
    redirect('/customer/orders')
  }

  // Driver display name via the safe card view (no phone/email exposed by RLS).
  let driver: { full_name?: string } | null = null
  if (order.driver_id) {
    const { data: card } = await supabase
      .from('safe_profile_cards')
      .select('display_name')
      .eq('id', order.driver_id)
      .maybeSingle()
    if (card) driver = { full_name: card.display_name ?? undefined }
  }

  // Fetch Items
  const { data: orderItems } = await supabase
    .from('order_items')
    .select('quantity, price_at_time, products(name)')
    .eq('order_id', order.id)

  // Fetch Payment
  const { data: payments } = await supabase
    .from('payments')
    .select('status, method, amount')
    .eq('order_id', order.id)
    .limit(1)

  const payment = payments?.[0]

  // Helpers
  const pickup = (order.pickup_location as { address?: string })?.address || 'Unknown'
  const dropoff = (order.dropoff_location as { address?: string })?.address || 'Unknown'

  const getServiceIcon = (type: string) => {
    switch (type) {
      case 'ride': return <Car className="h-8 w-8" />
      case 'eats': return <Utensils className="h-8 w-8" />
      case 'grocery': return <ShoppingBasket className="h-8 w-8" />
      default: return <Package className="h-8 w-8" />
    }
  }

  const getStatusDisplay = (status: string) => {
    switch(status) {
      case 'pending': return { label: 'Finding a Partner...', color: 'text-yellow-500', bg: 'bg-yellow-500/20' }
      case 'accepted': return { label: 'Partner Assigned', color: 'text-blue-500', bg: 'bg-blue-500/20' }
      case 'preparing': return { label: 'Preparing', color: 'text-orange-500', bg: 'bg-orange-500/20' }
      case 'ready': return { label: 'Ready for Pickup', color: 'text-teal-500', bg: 'bg-teal-500/20' }
      case 'in_transit': return { label: 'In Transit', color: 'text-purple-500', bg: 'bg-purple-500/20' }
      case 'completed': return { label: 'Completed', color: 'text-green-500', bg: 'bg-green-500/20' }
      case 'cancelled': return { label: 'Cancelled', color: 'text-red-500', bg: 'bg-red-500/20' }
      default: return { label: 'Unknown', color: 'text-gray-500', bg: 'bg-gray-500/20' }
    }
  }

  const statusInfo = getStatusDisplay(order.status)
  const isCancellable = order.status === 'pending' || order.status === 'accepted'

  const subtotal = orderItems?.reduce((sum, item) => sum + (item.price_at_time * item.quantity), 0) || 0
  const deliveryFee = 2.99
  const serviceFee = subtotal * 0.10
  const tax = subtotal * 0.08875
  const tip = 3.00 // Default demo tip

  return (
    <div className="max-w-2xl mx-auto space-y-6 pb-20 animate-in fade-in slide-in-from-bottom-4">
      <AutoRefresh intervalMs={5000} />
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Order Tracking</h1>
        <div className={`px-4 py-1.5 rounded-full text-sm font-bold flex items-center gap-2 ${statusInfo.bg} ${statusInfo.color}`}>
          {order.status === 'in_transit' || order.status === 'pending' || order.status === 'preparing' ? (
            <span className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-current`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 bg-current`}></span>
            </span>
          ) : null}
          {statusInfo.label}
        </div>
      </div>

      <GlassCard className="relative overflow-hidden flex flex-col items-center justify-center p-1 aspect-video rounded-2xl border-primary/20">
        <div className="absolute inset-0 z-0">
          <SafeLeafletMap 
            center={[
              ((order.pickup_location as { lat?: number; lng?: number })?.lat || 40.7128), 
              ((order.pickup_location as { lat?: number; lng?: number })?.lng || -74.0060)
            ]} 
            markers={[
              { position: [((order.pickup_location as { lat?: number; lng?: number })?.lat || 40.7128), ((order.pickup_location as { lat?: number; lng?: number })?.lng || -74.0060)], label: 'Pickup' },
              { position: [((order.dropoff_location as { lat?: number; lng?: number })?.lat || 40.7128), ((order.dropoff_location as { lat?: number; lng?: number })?.lng || -74.0060)], label: 'Dropoff' }
            ]}
            height="100%"
          />
        </div>
        <div className="relative z-10 p-6 bg-background/80 backdrop-blur-md rounded-2xl border text-center shadow-2xl mt-auto mb-4">
          <div className={`p-4 rounded-full mb-4 inline-flex ${statusInfo.bg} ${statusInfo.color}`}>
            {getServiceIcon(order.service_type)}
          </div>
          <h2 className="text-xl font-bold capitalize">
            {order.merchants?.name || `${order.service_type} Request`}
          </h2>
          <p className="text-muted-foreground mt-1">Order ID: {order.id.split('-')[0]}</p>
        </div>
      </GlassCard>

      <div className="grid gap-4">
        {/* Timeline / Driver */}
        <GlassCard className="p-6">
          <h3 className="font-bold mb-4 flex items-center gap-2"><Clock className="w-5 h-5"/> Timeline & Driver</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground">Order Placed</span>
              <span className="font-medium">{new Date(order.created_at).toLocaleTimeString()}</span>
            </div>
            {driver && (
              <div className="p-3 bg-primary/10 rounded-lg flex justify-between items-center mt-2">
                <div>
                  <p className="text-sm text-muted-foreground">Assigned Partner</p>
                  <p className="font-bold">{driver.full_name}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground mb-1">Contact</p>
                  <Button size="sm" variant="outline">Call</Button>
                </div>
              </div>
            )}
          </div>
        </GlassCard>

        {/* Locations */}
        <GlassCard className="p-6 space-y-6">
          <div className="flex items-start gap-4">
            <div className="mt-1 bg-primary/20 p-2 rounded-full text-primary">
              <MapPin className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground font-medium">Pickup</p>
              <p className="font-semibold text-lg">{pickup}</p>
            </div>
          </div>
          
          <div className="flex items-start gap-4">
            <div className="mt-1 bg-destructive/20 p-2 rounded-full text-destructive">
              <Navigation className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground font-medium">Dropoff</p>
              <p className="font-semibold text-lg">{dropoff}</p>
            </div>
          </div>
        </GlassCard>

        {/* Order Items & Receipt */}
        {(order.service_type === 'eats' || order.service_type === 'grocery') && (
          <GlassCard className="p-6">
            <h3 className="font-bold mb-4 flex items-center gap-2 border-b border-primary/10 pb-2"><Receipt className="w-5 h-5"/> Order Details</h3>
            <div className="space-y-3 text-sm">
              {(orderItems as unknown as Array<{ quantity: number; price_at_time: number; products?: { name?: string } | null }> | null)?.map((item, i) => (
                <div key={i} className="flex justify-between items-start">
                  <div className="flex gap-2">
                    <span className="font-bold text-primary">{item.quantity}x</span>
                    <span>{item.products?.name || 'Unknown Item'}</span>
                  </div>
                  <span className="font-medium">${(item.price_at_time * item.quantity).toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div className="pt-4 mt-4 border-t border-primary/10 space-y-2 text-sm text-muted-foreground">
              <div className="flex justify-between"><span>Subtotal</span><span>${subtotal.toFixed(2)}</span></div>
              <div className="flex justify-between"><span>Delivery Fee</span><span>${deliveryFee.toFixed(2)}</span></div>
              <div className="flex justify-between"><span>Service Fee</span><span>${serviceFee.toFixed(2)}</span></div>
              <div className="flex justify-between"><span>Estimated Tax</span><span>${tax.toFixed(2)}</span></div>
              <div className="flex justify-between"><span>Tip</span><span>${tip.toFixed(2)}</span></div>
            </div>
          </GlassCard>
        )}

        <GlassCard className="p-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Total Payment</p>
            <p className="font-bold text-2xl">${(order.total_amount || 0).toFixed(2)}</p>
            {payment && (
              <p className="text-xs uppercase tracking-wide font-bold mt-1 text-primary">
                {payment.method} • {payment.status}
              </p>
            )}
          </div>
          <div className="flex gap-2 w-full md:w-auto">
            <Button variant="outline" className="flex-1 md:flex-none text-destructive hover:bg-destructive hover:text-white border-destructive"><ShieldAlert className="w-4 h-4 mr-2"/> Support</Button>
            {isCancellable && (
              <div className="flex-1 md:flex-none">
                <CancelOrderButton orderId={order.id} />
              </div>
            )}
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
