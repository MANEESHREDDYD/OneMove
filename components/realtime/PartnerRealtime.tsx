'use client'

import { useRealtimePartnerJobs } from "@/hooks/useRealtimePartnerJobs"

export function PartnerRealtime({ driverId }: { driverId: string }) {
  useRealtimePartnerJobs(driverId)
  return null
}
