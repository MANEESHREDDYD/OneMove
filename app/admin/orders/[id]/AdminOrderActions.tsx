'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { adminUpdateOrderStatus } from './actions'
import { AlertCircle, RefreshCw, CheckCircle, DollarSign } from 'lucide-react'
import { useRouter } from 'next/navigation'

export function AdminOrderActions({ orderId, currentStatus, serviceType }: { orderId: string, currentStatus: string, serviceType: string }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  async function handleUpdate(newStatus: string) {
    setLoading(true)
    setError(null)
    const res = await adminUpdateOrderStatus(orderId, newStatus)
    if (res?.error) {
      setError(res.error)
    } else {
      router.refresh()
    }
    setLoading(false)
  }

  const getAvailableStatuses = () => {
    if (serviceType === 'ride') {
      return ['requested', 'assigned', 'accepted', 'arrived', 'started', 'completed', 'cancelled']
    } else if (serviceType === 'courier') {
      return ['created', 'partner_assigned', 'accepted', 'picked_up', 'in_transit', 'delivered', 'cancelled']
    } else {
      return ['placed', 'merchant_accepted', 'preparing', 'ready', 'partner_assigned', 'picked_up', 'in_transit', 'delivered', 'cancelled', 'refunded']
    }
  }

  const availableStatuses = getAvailableStatuses()

  return (
    <div className="space-y-4">
      {error && (
        <div className="p-2 bg-destructive/10 border border-destructive text-destructive rounded-lg flex items-start gap-2 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <p>{error}</p>
        </div>
      )}
      
      <div className="space-y-2">
        <label className="text-xs font-bold text-muted-foreground uppercase">Force Update Status</label>
        <div className="grid grid-cols-2 gap-2">
          {availableStatuses.map(status => (
            <Button 
              key={status}
              variant={currentStatus === status ? "default" : "outline"}
              size="sm"
              onClick={() => handleUpdate(status)}
              disabled={loading || currentStatus === status}
              className="text-xs capitalize"
            >
              {currentStatus === status && <CheckCircle className="w-3 h-3 mr-1" />}
              {status.replace('_', ' ')}
            </Button>
          ))}
        </div>
      </div>

      <div className="pt-4 border-t border-primary/10 space-y-2">
         <label className="text-xs font-bold text-muted-foreground uppercase">Other Actions</label>
         <Button variant="secondary" size="sm" className="w-full justify-start text-xs" disabled={loading} onClick={() => router.refresh()}>
           <RefreshCw className="w-3 h-3 mr-2" /> Refresh Data
         </Button>
         <Button variant="destructive" size="sm" className="w-full justify-start text-xs" disabled={loading} onClick={async () => {
           setLoading(true)
           const { adminRefundPayment } = await import('./actions')
           const res = await adminRefundPayment(orderId)
           if (res?.error) setError(res.error)
           else router.refresh()
           setLoading(false)
         }}>
           <DollarSign className="w-3 h-3 mr-2" /> Refund Demo Payment
         </Button>
      </div>
    </div>
  )
}
