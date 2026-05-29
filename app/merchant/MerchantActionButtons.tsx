'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { updateMerchantOrderStatus } from './actions'
import { AlertCircle, ChefHat, CheckSquare } from 'lucide-react'

export function MerchantActionButtons({ orderId, currentStatus }: { orderId: string, currentStatus: string }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleUpdate(newStatus: 'preparing' | 'ready') {
    setLoading(true)
    setError(null)
    const res = await updateMerchantOrderStatus(orderId, newStatus)
    if (res?.error) {
      setError(res.error)
      setLoading(false)
    }
  }

  return (
    <div className="space-y-2 w-full mt-4">
      {error && (
        <div className="p-2 bg-destructive/10 border border-destructive text-destructive rounded-lg flex items-start gap-2 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <p>{error}</p>
        </div>
      )}
      
      {currentStatus === 'pending' || currentStatus === 'accepted' ? (
        <Button 
          className="w-full bg-orange-600 hover:bg-orange-700" 
          onClick={() => handleUpdate('preparing')}
          disabled={loading}
        >
          <ChefHat className="w-4 h-4 mr-2" />
          {loading ? 'Updating...' : 'Start Preparing'}
        </Button>
      ) : null}

      {currentStatus === 'preparing' && (
        <Button 
          className="w-full bg-green-600 hover:bg-green-700" 
          onClick={() => handleUpdate('ready')}
          disabled={loading}
        >
          <CheckSquare className="w-4 h-4 mr-2" />
          {loading ? 'Updating...' : 'Mark as Ready'}
        </Button>
      )}
    </div>
  )
}
