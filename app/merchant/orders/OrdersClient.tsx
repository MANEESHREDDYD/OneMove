'use client'

import { useState } from "react"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { updateMerchantOrderStatus } from "../actions"
import { Loader2 } from "lucide-react"

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function OrdersClient({ orders }: { orders: any[] }) {
  const [loadingId, setLoadingId] = useState<string | null>(null)

  const handleUpdate = async (id: string, newStatus: 'preparing' | 'ready') => {
    setLoadingId(id)
    await updateMerchantOrderStatus(id, newStatus)
    setLoadingId(null)
  }

  return (
    <div className="space-y-4">
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
                {['pending', 'accepted'].includes(order.status) && (
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
