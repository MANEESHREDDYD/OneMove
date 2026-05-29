import * as React from "react"
import { GlassCard } from "./GlassCard"
import { Skeleton } from "@/components/ui/skeleton"

export function LoadingCard() {
  return (
    <GlassCard className="p-6 space-y-4">
      <Skeleton className="h-10 w-10 rounded-full" />
      <Skeleton className="h-6 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
    </GlassCard>
  )
}
