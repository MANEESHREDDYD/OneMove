'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/utils/supabase/client'

export function useRealtimePartnerJobs(driverId: string | null) {
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    if (!driverId) return

    // Listen for new pending/ready jobs that are unassigned
    const channel = supabase
      .channel('public:orders:partner')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'orders',
        },
        (payload) => {
          // If a new job was created or updated
          const newRow = payload.new as Record<string, unknown>;
          if (newRow && (newRow.driver_id === null || newRow.driver_id === driverId)) {
             router.refresh()
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [driverId, router, supabase])
}
