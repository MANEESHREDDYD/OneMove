'use client'

import { useState } from "react"
import { useRouter } from "next/navigation"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { acceptJob, updateJobStatus } from "../actions"
import { AlertCircle, CheckCircle2, Navigation, Loader2 } from "lucide-react"
import { useRealtimePartnerJobs } from "@/hooks/useRealtimePartnerJobs"

export function JobsClient({ 
  availableJobs, 
  activeJobs,
  driverId
}: { 
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  availableJobs: any[],
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  activeJobs: any[],
  driverId: string
}) {
  const router = useRouter()
  useRealtimePartnerJobs(driverId)
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleAccept = async (id: string) => {
    setLoadingId(id)
    setError(null)
    const result = await acceptJob(id)
    if (result?.error) setError(result.error)
    else router.refresh()
    setLoadingId(null)
  }

  const handleUpdate = async (id: string, newStatus: string) => {
    setLoadingId(id)
    setError(null)
    const result = await updateJobStatus(id, newStatus)
    if (result?.error) setError(result.error)
    else router.refresh()
    setLoadingId(null)
  }

  return (
    <div className="space-y-8">
      {error && (
        <GlassCard className="border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          <div className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <p>{error}</p>
          </div>
        </GlassCard>
      )}

      {/* Active Jobs */}
      {activeJobs.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-primary">Your Active Jobs</h2>
          <div className="grid gap-4">
            {activeJobs.map(job => (
              <GlassCard key={job.id} className="p-5 border-primary/40 ring-1 ring-primary/20">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <span className="bg-primary/20 text-primary px-2 py-1 rounded-md text-xs font-bold uppercase">{job.service_type}</span>
                    <h3 className="font-bold text-lg mt-2">Order {job.id.split('-')[0]}</h3>
                    <p className="text-sm text-muted-foreground mt-1 font-medium text-purple-400">Status: {job.status}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-black text-primary">${job.total_amount?.toFixed(2)}</p>
                  </div>
                </div>
                
                <div className="space-y-2 mb-4 text-sm bg-background/50 p-3 rounded-lg">
                   <div className="flex gap-2"><Navigation className="w-4 h-4 text-primary" /> <span className="line-clamp-1">{job.pickup_location?.address}</span></div>
                   <div className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-green-500" /> <span className="line-clamp-1">{job.dropoff_location?.address}</span></div>
                </div>

                <div className="flex gap-2">
                  {job.status === 'accepted' && <Button className="flex-1" onClick={() => handleUpdate(job.id, 'in_transit')} disabled={loadingId === job.id}>Start Transit</Button>}
                  {job.status === 'in_transit' && <Button className="flex-1 bg-green-600 hover:bg-green-700 text-white" onClick={() => handleUpdate(job.id, 'completed')} disabled={loadingId === job.id}>Mark Completed</Button>}
                  {job.status === 'preparing' && <Button variant="outline" className="flex-1" disabled>Waiting for Merchant</Button>}
                  {job.status === 'ready' && <Button className="flex-1" onClick={() => handleUpdate(job.id, 'in_transit')} disabled={loadingId === job.id}>Pick Up & Start Transit</Button>}
                </div>
              </GlassCard>
            ))}
          </div>
        </div>
      )}

      {/* Available Jobs */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold">Available Jobs Near You</h2>
        {availableJobs.length === 0 ? (
          <GlassCard className="p-8 text-center text-muted-foreground">
            No jobs currently available. You will be notified when new jobs appear.
          </GlassCard>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {availableJobs.map(job => (
              <GlassCard key={job.id} className="p-5 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <span className="bg-secondary/50 px-2 py-1 rounded-md text-xs font-bold uppercase">{job.service_type}</span>
                      <h3 className="font-bold text-base mt-2">Order {job.id.split('-')[0]}</h3>
                    </div>
                    <p className="text-xl font-bold">${job.total_amount?.toFixed(2)}</p>
                  </div>
                  <div className="text-sm text-muted-foreground space-y-1 mb-4">
                    <p className="truncate">From: {job.pickup_location?.address}</p>
                    <p className="truncate">To: {job.dropoff_location?.address}</p>
                  </div>
                </div>
                <Button 
                  className="w-full font-bold" 
                  onClick={() => handleAccept(job.id)}
                  disabled={loadingId === job.id}
                >
                  {loadingId === job.id ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Accept Job'}
                </Button>
              </GlassCard>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
