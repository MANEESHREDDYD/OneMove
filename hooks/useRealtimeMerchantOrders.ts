'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/utils/supabase/client'

export function useRealtimeMerchantOrders(merchantIds: string[]) {
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    if (merchantIds.length === 0) return

    // Listen for order updates for this merchant
    const channel = supabase
      .channel('public:orders:merchant')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'orders',
        },
        (payload) => {
          const newRow = payload.new as Record<string, unknown>;
          if (newRow && typeof newRow.merchant_id === 'string' && merchantIds.includes(newRow.merchant_id)) {
            router.refresh()
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [merchantIds, router, supabase])
}
