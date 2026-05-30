"use client"

import dynamic from 'next/dynamic'
import { LoadingCard } from '@/components/common/LoadingCard'

// Dynamically import the Leaflet map with SSR disabled to prevent server-side window errors
const CityCommandMap = dynamic(
  () => import('./CityCommandMap'),
  { 
    ssr: false,
    loading: () => <LoadingCard />
  }
)

export function LiveCityPreview() {
  return <CityCommandMap />
}
