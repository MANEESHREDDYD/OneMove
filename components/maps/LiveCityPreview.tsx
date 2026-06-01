'use client'

import dynamic from 'next/dynamic'
import { Skeleton } from "@/components/ui/skeleton"

const MapComponent = dynamic(() => import('./MapComponent'), { 
  ssr: false,
  loading: () => <Skeleton className="w-full h-full bg-muted animate-pulse" />
})

export function LiveCityPreview({ orders, merchants }: { orders?: any[], merchants?: any[] }) {
  return (
    <div className="w-full h-full relative">
      <MapComponent orders={orders} merchants={merchants} />
    </div>
  )
}
