import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { Car, Utensils, ShoppingBasket, Package, MapPin, Navigation } from "lucide-react"
import { AcceptJobButton, ActiveJobButtons } from "./JobActionButtons"
import { Database } from "@/types/database.types"

export default async function DriverDashboard() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // Fetch orders that are pending and have no driver assigned
  const { data: availableJobsData } = await supabase
    .from('orders')
    .select('*')
    .eq('status', 'pending')
    .is('driver_id', null)
    .order('created_at', { ascending: true })

  // Fetch orders that are actively assigned to THIS driver
  const { data: activeJobsData } = await supabase
    .from('orders')
    .select('*')
    .eq('driver_id', user.id)
    .in('status', ['accepted', 'in_transit'])
    .order('created_at', { ascending: false })

  const availableJobs = availableJobsData || []
  const activeJobs = activeJobsData || []

  const getServiceIcon = (type: string) => {
    switch (type) {
      case 'ride': return <Car className="h-5 w-5 text-primary" />
      case 'eats': return <Utensils className="h-5 w-5 text-primary" />
      case 'grocery': return <ShoppingBasket className="h-5 w-5 text-primary" />
      default: return <Package className="h-5 w-5 text-primary" />
    }
  }

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Partner Dashboard" 
          description="Manage your jobs"
        />
        <form action={signout}>
          <Button variant="ghost" className="rounded-full text-xs">Sign Out</Button>
        </form>
      </div>

      {/* Active Jobs Section - Takes priority visually */}
      {activeJobs.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-blue-500"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
            </span>
            <h2 className="text-lg font-semibold tracking-tight text-blue-500">Active Job</h2>
          </div>
          
          <div className="grid gap-4">
            {activeJobs.map((job) => (
              <GlassCard key={job.id} className="p-6 border-blue-500/30 bg-blue-500/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-bl-full -z-10" />
                
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className="bg-blue-500/20 p-2 rounded-full">
                      {getServiceIcon(job.service_type)}
                    </div>
                    <div>
                      <h3 className="font-bold capitalize">{job.service_type} Delivery</h3>
                      <p className="text-xs text-muted-foreground uppercase tracking-wider">{job.status.replace('_', ' ')}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-xl text-blue-500">${job.total_amount?.toFixed(2)}</p>
                  </div>
                </div>

                <div className="space-y-3 mb-6">
                  <div className="flex items-start gap-3">
                    <MapPin className="h-4 w-4 mt-1 text-muted-foreground shrink-0" />
                    <p className="text-sm">{(job.pickup_location as {address?: string})?.address || 'N/A'}</p>
                  </div>
                  <div className="flex items-start gap-3">
                    <Navigation className="h-4 w-4 mt-1 text-destructive shrink-0" />
                    <p className="text-sm">{(job.dropoff_location as {address?: string})?.address || 'N/A'}</p>
                  </div>
                </div>

                <ActiveJobButtons orderId={job.id} currentStatus={job.status} />
              </GlassCard>
            ))}
          </div>
        </div>
      )}

      {/* Available Market Jobs */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">Available Jobs</h2>
        {availableJobs.length === 0 ? (
          <GlassCard className="p-8 text-center border-dashed border-primary/20">
            <Car className="h-10 w-10 text-muted-foreground mx-auto mb-4 opacity-50" />
            <p className="font-semibold text-muted-foreground">No jobs available right now.</p>
            <p className="text-sm text-muted-foreground mt-1">Wait for new requests to appear.</p>
          </GlassCard>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {availableJobs.map((job) => (
              <GlassCard key={job.id} className="p-5 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-2">
                      <div className="bg-primary/10 p-2 rounded-md">
                        {getServiceIcon(job.service_type)}
                      </div>
                      <h3 className="font-semibold capitalize">{job.service_type}</h3>
                    </div>
                    <div className="font-bold text-lg">${job.total_amount?.toFixed(2)}</div>
                  </div>
                  
                  <div className="space-y-2 mb-6">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <MapPin className="h-3 w-3 shrink-0" />
                      <span className="truncate">{(job.pickup_location as {address?: string})?.address || 'N/A'}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Navigation className="h-3 w-3 shrink-0 text-destructive/80" />
                      <span className="truncate">{(job.dropoff_location as {address?: string})?.address || 'N/A'}</span>
                    </div>
                  </div>
                </div>
                
                {/* Prevent accepting more jobs if already busy */}
                {activeJobs.length > 0 ? (
                  <Button variant="secondary" disabled className="w-full">
                    Finish active job first
                  </Button>
                ) : (
                  <AcceptJobButton orderId={job.id} />
                )}
              </GlassCard>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
