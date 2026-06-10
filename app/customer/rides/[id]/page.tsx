import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { PageHeader } from '@/components/common/PageHeader'
import { GlassCard } from '@/components/common/GlassCard'
import { SafeLeafletMap } from '@/components/maps/SafeLeafletMap'
import { AutoRefresh } from '@/components/common/AutoRefresh'
import { calculateRideEstimate } from '@/utils/pricing'
import { MapPin, Navigation, Car, Clock, CreditCard, Activity, HelpCircle, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default async function CustomerRideDetail({ params }: { params: Promise<{ id: string }> }) {
  const supabase = await createClient()
  if (!supabase) return redirect('/auth/login')

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return redirect('/auth/login')

  const resolvedParams = await params

  const { data: order, error } = await supabase
    .from('orders')
    .select('*, order_status_events(*), driver:profiles!orders_driver_id_fkey(*), payments(*)')
    .eq('id', resolvedParams.id)
    .single()

  if (error || !order) {
    return (
      <div className="p-8 text-center text-muted-foreground flex flex-col items-center justify-center min-h-[400px]">
        <Activity className="w-12 h-12 mb-4 opacity-50" />
        <p>Ride not found (ID: {resolvedParams.id})</p>
      </div>
    )
  }

  const pickup = order.pickup_location as { lat?: number; lng?: number; address?: string } | null
  const dropoff = order.dropoff_location as { lat?: number; lng?: number; address?: string } | null

  const markers = []
  if (pickup?.lat && pickup?.lng) markers.push({ position: [pickup.lat, pickup.lng] as [number, number], label: 'Pickup' })
  if (dropoff?.lat && dropoff?.lng) markers.push({ position: [dropoff.lat, dropoff.lng] as [number, number], label: 'Dropoff' })
  
  const mapCenter = markers.length > 0 ? markers[0].position : [40.7128, -74.0060]
  const polyline: [number, number][] | undefined = (pickup?.lat && pickup?.lng && dropoff?.lat && dropoff?.lng) ? [[pickup.lat, pickup.lng], [dropoff.lat, dropoff.lng]] : undefined

  // Infer the service class or recalculate breakdown
  const estimate = pickup && dropoff ? calculateRideEstimate(pickup.address ?? '', dropoff.address ?? '') : null
  const payment = order.payments?.[0]
  
  // Guess class by matching total to estimate prices
  let serviceClass = 'economy'
  if (estimate) {
    const total = order.total_amount
    if (Math.abs(total - estimate.prices.premium.total) < 1) serviceClass = 'premium'
    else if (Math.abs(total - estimate.prices.xl.total) < 1) serviceClass = 'xl'
    else if (Math.abs(total - estimate.prices.comfort.total) < 1) serviceClass = 'comfort'
  }
  const breakdown = estimate?.prices[serviceClass as keyof typeof estimate.prices]

  const statusColor = order.status === 'completed' ? 'text-green-500' : order.status === 'cancelled' ? 'text-destructive' : 'text-primary'

  return (
    <div className="space-y-6 pb-20 max-w-4xl mx-auto">
      <AutoRefresh intervalMs={5000} />
      <div className="flex justify-between items-center">
        <PageHeader title="Ride Tracker" description={`ID: ${order.id.toUpperCase().split('-')[0]}`} />
        <span className={`px-4 py-1.5 rounded-full bg-muted font-bold text-sm uppercase tracking-widest ${statusColor}`}>
          {order.status}
        </span>
      </div>
      
      <GlassCard className="h-64 lg:h-80 relative overflow-hidden p-1">
        <SafeLeafletMap center={mapCenter as [number, number]} markers={markers} polyline={polyline} height="100%" />
      </GlassCard>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          <GlassCard className="p-6 space-y-4">
            <h3 className="font-bold flex items-center gap-2"><MapPin className="w-5 h-5 text-primary" /> Route</h3>
            <div className="space-y-4 relative before:absolute before:inset-0 before:ml-4 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
              <div className="flex items-center gap-4 relative">
                <div className="bg-background border-2 border-primary w-4 h-4 rounded-full ml-2.5 z-10"></div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Pickup</p>
                  <p className="font-medium">{pickup?.address || 'N/A'}</p>
                </div>
              </div>
              <div className="flex items-center gap-4 relative">
                <div className="bg-destructive border-2 border-destructive w-4 h-4 rounded-full ml-2.5 z-10"></div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase">Dropoff</p>
                  <p className="font-medium">{dropoff?.address || 'N/A'}</p>
                </div>
              </div>
            </div>
            {estimate && (
              <div className="pt-4 border-t flex justify-between text-sm text-muted-foreground">
                <span className="flex items-center gap-1"><Car className="w-4 h-4" /> {estimate.distanceMiles} miles</span>
                <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> ~{estimate.durationMinutes} mins</span>
              </div>
            )}
          </GlassCard>

          <GlassCard className="p-6 space-y-4">
            <h3 className="font-bold flex items-center gap-2"><Activity className="w-5 h-5 text-blue-500" /> Timeline</h3>
            <div className="space-y-3">
              {(order.order_status_events || []).map((ev: { created_at: string; status: string; notes?: string }, idx: number) => (
                <div key={idx} className="flex gap-4 text-sm">
                  <div className="w-16 text-muted-foreground text-xs">{new Date(ev.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                  <div>
                    <p className="font-medium capitalize">{ev.status}</p>
                    {ev.notes && <p className="text-xs text-muted-foreground">{ev.notes}</p>}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
        
        {/* Right Column */}
        <div className="space-y-6">
          <GlassCard className="p-6 space-y-4">
            <h3 className="font-bold flex items-center gap-2"><Car className="w-5 h-5 text-orange-500" /> Partner Assignment</h3>
            {order.driver ? (
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center font-bold text-xl text-primary">
                  {order.driver.full_name?.charAt(0)}
                </div>
                <div>
                  <p className="font-bold">{order.driver.full_name}</p>
                  <p className="text-sm text-muted-foreground capitalize">{serviceClass} Vehicle</p>
                </div>
              </div>
            ) : (
              <div className="text-center p-4 border border-dashed rounded-lg bg-muted/20">
                <div className="animate-pulse flex items-center justify-center gap-2 text-muted-foreground">
                  <div className="h-2 w-2 bg-primary rounded-full"></div>
                  <div className="h-2 w-2 bg-primary rounded-full animation-delay-200"></div>
                  <div className="h-2 w-2 bg-primary rounded-full animation-delay-400"></div>
                </div>
                <p className="text-sm mt-2 text-muted-foreground">Matching you with the best available partner...</p>
              </div>
            )}
          </GlassCard>

          <GlassCard className="p-6 space-y-4">
            <h3 className="font-bold flex items-center gap-2"><FileText className="w-5 h-5 text-green-500" /> Receipt Summary</h3>
            {breakdown ? (
              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="flex justify-between"><span>Base Fare</span><span>${breakdown.base.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>Distance</span><span>${breakdown.distance.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>Time</span><span>${breakdown.time.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>Platform Fee</span><span>${breakdown.platform.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>Taxes</span><span>${breakdown.tax.toFixed(2)}</span></div>
                <div className="flex justify-between font-bold text-lg text-foreground pt-2 border-t mt-2">
                  <span>Total</span>
                  <span>${order.total_amount?.toFixed(2)}</span>
                </div>
              </div>
            ) : (
              <div className="flex justify-between font-bold text-lg text-foreground pt-2">
                <span>Total</span>
                <span>${order.total_amount?.toFixed(2)}</span>
              </div>
            )}
            
            {payment && (
              <div className="pt-4 border-t mt-4 flex items-center justify-between text-sm">
                <span className="flex items-center gap-1 text-muted-foreground"><CreditCard className="w-4 h-4" /> {payment.method.replace('_', ' ')}</span>
                <span className={`uppercase font-semibold text-xs ${payment.status.includes('paid') ? 'text-green-500' : 'text-orange-500'}`}>
                  {payment.status.replace('_', ' ')}
                </span>
              </div>
            )}
          </GlassCard>

          <Button variant="outline" className="w-full h-12"><HelpCircle className="w-4 h-4 mr-2" /> Contact Support</Button>
        </div>
      </div>
    </div>
  )
}
