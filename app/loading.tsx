import { Loader2 } from 'lucide-react'

export default function Loading() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center p-8">
      <div className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        Loading OneMove workspace
      </div>
    </div>
  )
}
