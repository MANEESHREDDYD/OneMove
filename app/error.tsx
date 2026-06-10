'use client'

import { AlertTriangle, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { GlassCard } from '@/components/common/GlassCard'

export default function Error({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string }
  unstable_retry: () => void
}) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-6">
      <GlassCard className="max-w-lg p-8 text-center">
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full border border-red-500/30 bg-red-500/10 text-red-300">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <h1 className="text-2xl font-bold">Something went wrong</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          OneMove could not render this view. Try again, or return to the previous dashboard.
        </p>
        {error.digest && (
          <p className="mt-4 font-mono text-xs text-muted-foreground">Error digest: {error.digest}</p>
        )}
        <Button className="mt-6" onClick={() => unstable_retry()}>
          <RotateCcw className="mr-2 h-4 w-4" />
          Try again
        </Button>
      </GlassCard>
    </div>
  )
}
