'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { cancelOrder } from './actions'
import { useRouter } from 'next/navigation'
import { AlertCircle, XCircle } from 'lucide-react'

export function CancelOrderButton({ orderId }: { orderId: string }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  async function handleCancel() {
    if (!confirm('Are you sure you want to cancel this order?')) return
    setLoading(true)
    setError(null)
    
    const result = await cancelOrder(orderId)
    if (result.error) {
      setError(result.error)
      setLoading(false)
    } else {
      // Return to dashboard
      router.push('/customer')
    }
  }

  return (
    <div className="w-full space-y-2">
      {error && (
        <div className="p-3 bg-destructive/10 border border-destructive text-destructive rounded-lg flex items-start gap-2 text-sm animate-in fade-in">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}
      <Button 
        variant="destructive" 
        className="w-full" 
        size="lg"
        onClick={handleCancel}
        disabled={loading}
      >
        <XCircle className="w-5 h-5 mr-2" />
        {loading ? 'Canceling...' : 'Cancel Order'}
      </Button>
    </div>
  )
}
