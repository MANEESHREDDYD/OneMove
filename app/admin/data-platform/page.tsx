import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { PageHeader } from '@/components/common/PageHeader'
import { GlassCard } from '@/components/common/GlassCard'
import { Database, CheckCircle, XCircle, AlertTriangle, Clock } from 'lucide-react'
import { SetupRequired } from "@/components/common/SetupRequired"

export default async function DataPlatformPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  // Fetch recent pipeline runs
  const { data: pipelineRuns } = await supabase
    .from('data_pipeline_runs')
    .select('*')
    .order('start_time', { ascending: false })
    .limit(10)

  // Fetch data quality results
  const { data: qualityResults } = await supabase
    .from('data_quality_results')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(20)

  // Count raw table rows
  const [{ count: orderCount }, { count: itemCount }, { count: profileCount }] = await Promise.all([
    supabase.from('orders').select('*', { count: 'exact', head: true }),
    supabase.from('order_items').select('*', { count: 'exact', head: true }),
    supabase.from('profiles').select('*', { count: 'exact', head: true })
  ])

  const lastRefresh = pipelineRuns?.find(r => r.status === 'success')?.end_time
  const failingChecks = qualityResults?.filter(q => q.status === 'fail' || q.status === 'warning') || []

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Data Engineering Platform" 
        description="Pipeline monitoring, data quality, and table diagnostics."
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <GlassCard className="p-4 space-y-1">
          <p className="text-sm text-muted-foreground flex items-center gap-2"><Database className="w-4 h-4"/> Orders Rows</p>
          <p className="text-2xl font-bold">{orderCount?.toLocaleString() || 0}</p>
        </GlassCard>
        <GlassCard className="p-4 space-y-1">
          <p className="text-sm text-muted-foreground flex items-center gap-2"><Database className="w-4 h-4"/> Order Items Rows</p>
          <p className="text-2xl font-bold">{itemCount?.toLocaleString() || 0}</p>
        </GlassCard>
        <GlassCard className="p-4 space-y-1">
          <p className="text-sm text-muted-foreground flex items-center gap-2"><Database className="w-4 h-4"/> Profiles Rows</p>
          <p className="text-2xl font-bold">{profileCount?.toLocaleString() || 0}</p>
        </GlassCard>
        <GlassCard className="p-4 space-y-1">
          <p className="text-sm text-muted-foreground flex items-center gap-2"><Clock className="w-4 h-4"/> Last Refresh</p>
          <p className="text-sm font-medium mt-1">
            {lastRefresh ? new Date(lastRefresh).toLocaleString() : 'Pending...'}
          </p>
        </GlassCard>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Pipeline Runs */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            Recent Pipeline Runs
          </h2>
          <div className="space-y-3">
            {pipelineRuns?.map(run => (
              <GlassCard key={run.id} className="p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium text-sm font-mono">{run.pipeline_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(run.start_time).toLocaleString()}
                  </p>
                  {run.error_message && (
                    <p className="text-xs text-destructive mt-1 truncate max-w-[250px]">
                      {run.error_message}
                    </p>
                  )}
                </div>
                <div className="text-right">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    run.status === 'success' ? 'bg-green-500/10 text-green-500' :
                    run.status === 'failed' ? 'bg-red-500/10 text-red-500' : 'bg-blue-500/10 text-blue-500'
                  }`}>
                    {run.status.toUpperCase()}
                  </span>
                  <p className="text-xs text-muted-foreground mt-1">
                    {run.rows_processed} rows
                  </p>
                </div>
              </GlassCard>
            ))}
            {(!pipelineRuns || pipelineRuns.length === 0) && (
              <p className="text-sm text-muted-foreground p-4 text-center border rounded-lg border-dashed">No pipeline runs found. Run `npm run pipeline:all`</p>
            )}
          </div>
        </div>

        {/* Data Quality */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            Data Quality Anomalies
          </h2>
          <div className="space-y-3">
            {failingChecks.length === 0 && (qualityResults?.length ?? 0) > 0 ? (
              <GlassCard className="p-6 text-center border-green-500/20">
                <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="font-medium text-green-500">All Quality Checks Passed</p>
              </GlassCard>
            ) : null}
            
            {failingChecks.map(check => (
              <GlassCard key={check.id} className={`p-4 border-l-4 ${check.severity === 'critical' ? 'border-l-red-500' : 'border-l-yellow-500'}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium text-sm flex items-center gap-1">
                      {check.severity === 'critical' ? <XCircle className="w-4 h-4 text-red-500"/> : <AlertTriangle className="w-4 h-4 text-yellow-500"/>}
                      {check.check_name}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1">Table: {check.affected_table}</p>
                    <p className="text-xs text-muted-foreground mt-1 font-mono bg-muted p-1 rounded inline-block">
                      {check.recommended_fix}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-destructive">{check.failed_rows_count}</p>
                    <p className="text-xs text-muted-foreground">failed rows</p>
                  </div>
                </div>
              </GlassCard>
            ))}

            {(!qualityResults || qualityResults.length === 0) && (
              <p className="text-sm text-muted-foreground p-4 text-center border rounded-lg border-dashed">No quality checks found.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
