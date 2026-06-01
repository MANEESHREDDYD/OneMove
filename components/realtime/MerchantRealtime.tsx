'use client'

import { useRealtimeMerchantOrders } from "@/hooks/useRealtimeMerchantOrders"

export function MerchantRealtime({ merchantIds }: { merchantIds: string[] }) {
  useRealtimeMerchantOrders(merchantIds)
  return null
}
