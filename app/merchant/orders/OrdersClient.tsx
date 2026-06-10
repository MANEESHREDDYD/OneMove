'use client'

import { useState } from "react"
import { useRouter } from "next/navigation"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { updateMerchantOrderStatus } from "../actions"
import { AlertCircle, Loader2 } from "lucide-react"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function OrdersClient({ orders }: { orders: any[] }) {
  const router = useRouter()
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleUpdate = async (id: string, newStatus: 'merchant_accepted' | 'preparing' | 'ready') => {
    setLoadingId(id)
    setError(null)
    const result = await updateMerchantOrderStatus(id, newStatus)
    if (result?.error) {
      setError(result.error)
    } else {
      router.refresh()
    }
    setLoadingId(null)
  }

  return (
    <div className="space-y-4">
      {error && (
        <GlassCard className="border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <div className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{error}</p>
          </div>
        </GlassCard>
      )}

      {orders.length === 0 ? (
        <GlassCard className="p-8 text-center text-muted-foreground">
          No active orders at the moment.
        </GlassCard>
      ) : (
        <div className="grid gap-4">
          {orders.map(order => (
            <GlassCard key={order.id} className="p-5">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-bold text-lg">Order {order.id.split('-')[0]}</h3>
                  <p className="text-sm font-medium mt-1 uppercase text-primary">Status: {order.status}</p>
                  <p className="text-sm text-muted-foreground mt-1">Total: ${order.total_amount?.toFixed(2)}</p>
                </div>
              </div>

              <div className="flex gap-2">
                {['pending', 'placed'].includes(order.status) && (
                  <Button 
                    className="flex-1 bg-blue-600 hover:bg-blue-700 text-white" 
                    onClick={() => handleUpdate(order.id, 'merchant_accepted')}
                    disabled={loadingId === order.id}
                  >
                    {loadingId === order.id ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Accept Order'}
                  </Button>
                )}
                {['merchant_accepted', 'accepted'].includes(order.status) && (
                  <Button 
                    className="flex-1" 
                    onClick={() => handleUpdate(order.id, 'preparing')}
                    disabled={loadingId === order.id}
                  >
                    {loadingId === order.id ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Start Preparing'}
                  </Button>
                )}
                {order.status === 'preparing' && (
                  <Button 
                    className="flex-1 bg-green-600 hover:bg-green-700 text-white" 
                    onClick={() => handleUpdate(order.id, 'ready')}
                    disabled={loadingId === order.id}
                  >
                    {loadingId === order.id ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Mark as Ready'}
                  </Button>
                )}
                {order.status === 'ready' && (
                  <Button variant="outline" className="flex-1" disabled>
                    Waiting for Driver
                  </Button>
                )}
                {order.status === 'in_transit' && (
                  <Button variant="outline" className="flex-1" disabled>
                    Out for Delivery
                  </Button>
                )}
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  )
}
