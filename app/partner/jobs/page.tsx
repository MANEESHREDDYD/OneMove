import { PageHeader } from "@/components/common/PageHeader"
import { createClient } from "@/utils/supabase/server"
import { SetupRequired } from "@/components/common/SetupRequired"
import { redirect } from "next/navigation"
import { JobsClient } from "./JobsClient"
import { AutoRefresh } from "@/components/common/AutoRefresh"

export const dynamic = "force-dynamic"

export default async function AvailableJobsPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  // Get active jobs for this driver
  const { data: activeJobs } = await supabase
    .from('orders')
    .select('*')
    .eq('driver_id', user.id)
    .in('status', ['accepted', 'preparing', 'ready', 'in_transit'])
    .order('created_at', { ascending: false })

  // Get pending jobs
  const { data: availableJobs } = await supabase
    .from('orders')
    .select('*')
    .in('status', ['pending', 'ready', 'requested'])
    .or(`driver_id.is.null,driver_id.eq.${user.id}`)
    .order('created_at', { ascending: false })
    .limit(20)

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <AutoRefresh intervalMs={5000} />
      <PageHeader 
        title="Job Marketplace" 
        description="Find and manage your deliveries and rides"
      />
      <JobsClient availableJobs={availableJobs || []} activeJobs={activeJobs || []} driverId={user.id} />
    </div>
  )
}
