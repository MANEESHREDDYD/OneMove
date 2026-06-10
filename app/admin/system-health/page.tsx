import { redirect } from 'next/navigation'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Database,
  GitCommit,
  ShieldCheck,
  XCircle,
} from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { GlassCard } from '@/components/common/GlassCard'
import { SetupRequired } from '@/components/common/SetupRequired'
import { createClient } from '@/utils/supabase/server'
import { getSystemHealthSnapshot, type HealthCheck, type HealthStatus } from '@/lib/systemHealth'

export const dynamic = 'force-dynamic'

function statusClasses(status: HealthStatus) {
  switch (status) {
    case 'pass':
      return 'border-green-500/30 bg-green-500/10 text-green-300'
    case 'warn':
      return 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300'
    case 'fail':
      return 'border-red-500/30 bg-red-500/10 text-red-300'
  }
}

function StatusIcon({ status }: { status: HealthStatus }) {
  if (status === 'pass') return <CheckCircle2 className="h-4 w-4" />
  if (status === 'warn') return <AlertTriangle className="h-4 w-4" />
  return <XCircle className="h-4 w-4" />
}

function StatusPill({ status }: { status: HealthStatus }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs font-bold uppercase ${statusClasses(status)}`}>
      <StatusIcon status={status} />
      {status}
    </span>
  )
}

function CheckRow({ check }: { check: HealthCheck }) {
  return (
    <div className="flex flex-col gap-3 border-b border-white/10 py-3 last:border-0 md:flex-row md:items-center md:justify-between">
      <div className="min-w-0">
        <p className="font-medium">{check.name}</p>
        <p className="mt-1 text-sm text-muted-foreground">{check.detail}</p>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        {check.value !== undefined && (
          <span className="text-sm font-semibold text-muted-foreground">{check.value}</span>
        )}
        <StatusPill status={check.status} />
      </div>
    </div>
  )
}

function CheckSection({
  title,
  icon,
  checks,
}: {
  title: string
  icon: React.ReactNode
  checks: HealthCheck[]
}) {
  return (
    <GlassCard className="p-5">
      <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
        {icon}
        {title}
      </h2>
      <div>{checks.map((check) => <CheckRow key={`${title}-${check.name}`} check={check} />)}</div>
    </GlassCard>
  )
}

export default async function AdminSystemHealthPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) redirect('/auth/login')

  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single()

  if (profile?.role !== 'admin') {
    redirect(`/${profile?.role === 'driver' ? 'partner' : profile?.role || 'customer'}`)
  }

  const snapshot = await getSystemHealthSnapshot()
  const headlineStatus: HealthStatus =
    snapshot.summary.fail > 0 ? 'fail' : snapshot.summary.warn > 0 ? 'warn' : 'pass'

  return (
    <div className="space-y-8 pb-20">
      <PageHeader
        title="System Health"
        description="Local production-preview readiness checks. This is deterministic demo observability, not production APM."
      />

      <div className="grid gap-4 md:grid-cols-4">
        <GlassCard className="p-5">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Activity className="h-4 w-4" />
            Overall
          </p>
          <div className="mt-4">
            <StatusPill status={headlineStatus} />
          </div>
        </GlassCard>
        <GlassCard className="p-5">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="h-4 w-4" />
            Passing
          </p>
          <p className="mt-3 text-3xl font-black">{snapshot.summary.pass}</p>
        </GlassCard>
        <GlassCard className="p-5">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <AlertTriangle className="h-4 w-4" />
            Warnings
          </p>
          <p className="mt-3 text-3xl font-black">{snapshot.summary.warn}</p>
        </GlassCard>
        <GlassCard className="p-5">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <XCircle className="h-4 w-4" />
            Failing
          </p>
          <p className="mt-3 text-3xl font-black">{snapshot.summary.fail}</p>
        </GlassCard>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <GlassCard className="p-5">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <GitCommit className="h-4 w-4" />
            Build Version
          </p>
          <p className="mt-3 font-mono text-xl font-bold">{snapshot.commitHash}</p>
        </GlassCard>
        <GlassCard className="p-5">
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            Generated
          </p>
          <p className="mt-3 font-mono text-sm">{snapshot.generatedAt}</p>
        </GlassCard>
      </div>

      <CheckSection
        title="Core Readiness"
        icon={<Database className="h-5 w-5 text-primary" />}
        checks={[
          snapshot.database,
          snapshot.pipeline,
          snapshot.latestMlRun,
          snapshot.latestDataQuality,
          snapshot.rlsTest,
        ]}
      />

      <CheckSection
        title="Required Tables"
        icon={<Database className="h-5 w-5 text-blue-300" />}
        checks={snapshot.requiredTables}
      />

      <CheckSection
        title="Demo Users"
        icon={<ShieldCheck className="h-5 w-5 text-green-300" />}
        checks={snapshot.demoUsers}
      />

      <CheckSection
        title="Local Observability"
        icon={<Activity className="h-5 w-5 text-purple-300" />}
        checks={snapshot.observability}
      />
    </div>
  )
}
