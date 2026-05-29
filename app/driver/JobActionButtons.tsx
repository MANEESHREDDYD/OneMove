'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { acceptJob, updateJobStatus } from './actions'
import { AlertCircle, CheckCircle2, Navigation } from 'lucide-react'

export function AcceptJobButton({ orderId }: { orderId: string }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleAccept() {
    setLoading(true)
    setError(null)
    const res = await acceptJob(orderId)
    if (res?.error) {
      setError(res.error)
      setLoading(false)
    }
  }

  return (
    <div className="space-y-2">
      {error && (
        <div className="p-2 bg-destructive/10 border border-destructive text-destructive rounded-lg flex items-start gap-2 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <p>{error}</p>
        </div>
      )}
      <Button 
        className="w-full" 
        onClick={handleAccept}
        disabled={loading}
      >
        {loading ? 'Accepting...' : 'Accept Job'}
      </Button>
    </div>
  )
}

export function ActiveJobButtons({ orderId, currentStatus }: { orderId: string, currentStatus: string }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleUpdate(newStatus: 'in_transit' | 'completed') {
    setLoading(true)
    setError(null)
    const res = await updateJobStatus(orderId, newStatus)
    if (res?.error) {
      setError(res.error)
      setLoading(false)
    }
  }

  return (
    <div className="space-y-2">
      {error && (
        <div className="p-2 bg-destructive/10 border border-destructive text-destructive rounded-lg flex items-start gap-2 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <p>{error}</p>
        </div>
      )}
      
      {currentStatus === 'accepted' && (
        <Button 
          className="w-full bg-blue-600 hover:bg-blue-700" 
          onClick={() => handleUpdate('in_transit')}
          disabled={loading}
        >
          <Navigation className="w-4 h-4 mr-2" />
          {loading ? 'Updating...' : 'Start Job (In Transit)'}
        </Button>
      )}

      {currentStatus === 'in_transit' && (
        <Button 
          className="w-full bg-green-600 hover:bg-green-700" 
          onClick={() => handleUpdate('completed')}
          disabled={loading}
        >
          <CheckCircle2 className="w-4 h-4 mr-2" />
          {loading ? 'Updating...' : 'Complete Job'}
        </Button>
      )}
    </div>
  )
}
