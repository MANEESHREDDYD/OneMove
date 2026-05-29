import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { GlassCard } from '@/components/common/GlassCard'
import { Car, Utensils, ShoppingBasket, Package, MapPin, Navigation, Clock, CheckCircle2 } from 'lucide-react'
import { CancelOrderButton } from './CancelOrderButton'

export default async function OrderTrackingPage({ params }: { params: { id: string } }) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  const { data: order, error } = await supabase
    .from('orders')
    .select('*')
    .eq('id', params.id)
    .single()

  // Protect against viewing other users' orders
  if (error || !order || order.customer_id !== user.id) {
    redirect('/customer')
  }

  // Helper to parse JSON locations
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
      case 'in_transit': return { label: 'In Transit', color: 'text-purple-500', bg: 'bg-purple-500/20' }
      case 'completed': return { label: 'Completed', color: 'text-green-500', bg: 'bg-green-500/20' }
      case 'cancelled': return { label: 'Cancelled', color: 'text-red-500', bg: 'bg-red-500/20' }
      default: return { label: 'Unknown', color: 'text-gray-500', bg: 'bg-gray-500/20' }
    }
  }

  const statusInfo = getStatusDisplay(order.status)
  const isCancellable = order.status === 'pending' || order.status === 'accepted'

  return (
    <div className="max-w-2xl mx-auto space-y-6 pb-20">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Order Tracking</h1>
        <div className={`px-4 py-1.5 rounded-full text-sm font-bold flex items-center gap-2 ${statusInfo.bg} ${statusInfo.color}`}>
          {order.status === 'in_transit' || order.status === 'pending' ? (
            <span className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-current`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 bg-current`}></span>
            </span>
          ) : null}
          {statusInfo.label}
        </div>
      </div>

      <GlassCard className="relative overflow-hidden flex flex-col items-center justify-center bg-primary/5 border border-primary/20 aspect-video rounded-2xl">
        <div className="absolute inset-0 bg-[url('https://maps.gstatic.com/mapfiles/transparent.png')] opacity-20 bg-repeat" />
        <div className="relative z-10 p-6 bg-background/80 backdrop-blur-md rounded-2xl border text-center shadow-2xl">
          <div className={`p-4 rounded-full mb-4 inline-flex ${statusInfo.bg} ${statusInfo.color}`}>
            {getServiceIcon(order.service_type)}
          </div>
          <h2 className="text-xl font-bold capitalize">{order.service_type} Request</h2>
          <p className="text-muted-foreground">Order ID: {order.id.split('-')[0]}</p>
        </div>
      </GlassCard>

      <div className="grid gap-4">
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

        <div className="grid grid-cols-2 gap-4">
          <GlassCard className="p-6 flex flex-col items-center justify-center text-center">
            <Clock className="h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">Est. Time</p>
            <p className="font-bold text-xl">15 min</p>
          </GlassCard>
          
          <GlassCard className="p-6 flex flex-col items-center justify-center text-center">
            <CheckCircle2 className="h-8 w-8 text-primary mb-2" />
            <p className="text-sm text-muted-foreground">Total Fare</p>
            <p className="font-bold text-xl">${order.total_amount?.toFixed(2) || '0.00'}</p>
          </GlassCard>
        </div>

        {isCancellable && (
          <div className="pt-4">
            <CancelOrderButton orderId={order.id} />
          </div>
        )}
      </div>
    </div>
  )
}
