import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { PageHeader } from '@/components/common/PageHeader'
import { GlassCard } from '@/components/common/GlassCard'
import { SafeLeafletMap } from '@/components/maps/SafeLeafletMap'
import { AutoRefresh } from '@/components/common/AutoRefresh'

export default async function CustomerRideDetail({ params }: { params: Promise<{ id: string }> }) {
  const supabase = await createClient()
  if (!supabase) return redirect('/auth/login')

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return redirect('/auth/login')

  const resolvedParams = await params

  const { data: order, error } = await supabase
    .from('orders')
    .select('*, order_status_events(*), driver:profiles!orders_driver_id_fkey(*)')
    .eq('id', resolvedParams.id)
    .single()

  if (error || !order) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Ride not found (ID: {resolvedParams.id})
      </div>
    )
  }

  const pickup = order.pickup_location as any
  const dropoff = order.dropoff_location as any

  const markers = []
  if (pickup?.lat && pickup?.lng) markers.push({ position: [pickup.lat, pickup.lng] as [number, number], label: 'Pickup' })
  if (dropoff?.lat && dropoff?.lng) markers.push({ position: [dropoff.lat, dropoff.lng] as [number, number], label: 'Dropoff' })
  
  const mapCenter = markers.length > 0 ? markers[0].position : [40.7128, -74.0060]

  return (
    <div className="space-y-6 pb-20">
      <AutoRefresh intervalMs={5000} />
      <PageHeader title="Ride Details" description={`Ride #${order.id.slice(0, 8)}`} />
      
      <GlassCard className="h-64 relative overflow-hidden">
        <SafeLeafletMap center={mapCenter as [number, number]} markers={markers} height="100%" />
      </GlassCard>

      <div className="grid md:grid-cols-2 gap-4">
        <GlassCard className="p-4 space-y-2">
          <h3 className="font-bold text-lg">Status: {order.status}</h3>
          <p className="text-sm">Driver: {order.driver ? order.driver.full_name : 'Assigning...'}</p>
          <p className="font-semibold mt-2">${order.total_amount?.toFixed(2)}</p>
        </GlassCard>
        
        <GlassCard className="p-4 space-y-2">
          <h3 className="font-bold">Locations</h3>
          <div className="text-sm text-muted-foreground">
            <p><span className="font-medium text-foreground">From:</span> {pickup?.address || 'N/A'}</p>
            <p><span className="font-medium text-foreground">To:</span> {dropoff?.address || 'N/A'}</p>
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
