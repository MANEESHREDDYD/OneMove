import { execSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { createClient } from '@supabase/supabase-js'

// The health probe intentionally inspects many dynamic table names. Supabase's
// generated table generics are too narrow for that audit-style access pattern.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type HealthSupabaseClient = any

export type HealthStatus = 'pass' | 'warn' | 'fail'

export type HealthCheck = {
  name: string
  status: HealthStatus
  detail: string
  value?: string | number
}

export type SystemHealthSnapshot = {
  generatedAt: string
  commitHash: string
  database: HealthCheck
  requiredTables: HealthCheck[]
  demoUsers: HealthCheck[]
  pipeline: HealthCheck
  latestMlRun: HealthCheck
  latestDataQuality: HealthCheck
  rlsTest: HealthCheck
  observability: HealthCheck[]
  summary: {
    pass: number
    warn: number
    fail: number
  }
}

export const REQUIRED_HEALTH_TABLES = [
  'profiles',
  'orders',
  'order_items',
  'payments',
  'order_status_events',
  'merchants',
  'products',
  'support_tickets',
  'daily_marketplace_metrics',
  'metric_snapshots',
  'data_pipeline_runs',
  'data_quality_results',
  'feature_snapshots',
  'recommendations',
  'customer_segments',
  'merchant_reliability_scores',
  'partner_trust_scores',
  'ml_pipeline_runs',
  'experiments',
  'experiment_metrics',
  'ops_insights',
]

export const REQUIRED_DEMO_USERS = [
  { email: 'customer@onemove.demo', role: 'customer' },
  { email: 'merchant@onemove.demo', role: 'merchant' },
  { email: 'partner@onemove.demo', role: 'driver' },
  { email: 'admin@onemove.demo', role: 'admin' },
]

type RlsStatusArtifact = {
  passed: boolean
  checkedAt: string
  failedChecks: number
  checks: string[]
}

function buildCheck(
  name: string,
  status: HealthStatus,
  detail: string,
  value?: string | number
): HealthCheck {
  return { name, status, detail, value }
}

export function getBuildCommitHash(): string {
  const fromEnv =
    process.env.VERCEL_GIT_COMMIT_SHA ||
    process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA ||
    process.env.GITHUB_SHA ||
    process.env.COMMIT_SHA

  if (fromEnv) return fromEnv.slice(0, 12)

  try {
    return execSync('git rev-parse --short=12 HEAD', {
      cwd: process.cwd(),
      stdio: ['ignore', 'pipe', 'ignore'],
    })
      .toString()
      .trim()
  } catch {
    return 'local-unknown'
  }
}

export function getRlsStatusArtifactPath() {
  return path.join(process.cwd(), '.next', 'cache', 'onemove', 'rls-status.json')
}

export function readRlsStatusArtifact(): RlsStatusArtifact | null {
  const artifactPath = getRlsStatusArtifactPath()
  if (!existsSync(artifactPath)) return null

  try {
    return JSON.parse(readFileSync(artifactPath, 'utf8')) as RlsStatusArtifact
  } catch {
    return null
  }
}

async function getTableCount(
  supabase: HealthSupabaseClient,
  table: string
): Promise<HealthCheck> {
  const { count, error } = await supabase
    .from(table)
    .select('*', { count: 'exact', head: true })

  if (error) {
    return buildCheck(table, 'fail', `Table is not reachable: ${error.message}`)
  }

  const rowCount = count ?? 0
  return buildCheck(
    table,
    rowCount > 0 ? 'pass' : 'warn',
    rowCount > 0 ? 'Reachable with data' : 'Reachable but empty',
    rowCount
  )
}

async function getDemoUserChecks(
  supabase: HealthSupabaseClient
): Promise<HealthCheck[]> {
  const { data, error } = await supabase.auth.admin.listUsers({ page: 1, perPage: 1000 })

  if (error) {
    return [
      buildCheck('Demo auth users', 'fail', `Could not list Supabase auth users: ${error.message}`),
    ]
  }

  const byEmail = new Map(
    ((data.users || []) as Array<{ email?: string }>).map((user) => [user.email, user])
  )

  return REQUIRED_DEMO_USERS.map((demoUser) => {
    const user = byEmail.get(demoUser.email)
    if (!user) {
      return buildCheck(demoUser.email, 'fail', `Missing primary ${demoUser.role} demo account`)
    }

    return buildCheck(demoUser.email, 'pass', `Primary ${demoUser.role} demo account exists`)
  })
}

async function getLatestPipelineCheck(
  supabase: HealthSupabaseClient
): Promise<HealthCheck> {
  const { data, error } = await supabase
    .from('data_pipeline_runs')
    .select('pipeline_name, status, end_time, start_time, rows_processed')
    .order('start_time', { ascending: false })
    .limit(1)

  if (error) return buildCheck('Pipeline status', 'fail', error.message)
  const latest = data?.[0] as
    | {
        pipeline_name?: string
        status?: string
        end_time?: string | null
        start_time?: string
        rows_processed?: number | null
      }
    | undefined
  if (!latest) return buildCheck('Pipeline status', 'warn', 'No data pipeline runs recorded')

  const status = latest.status === 'success' ? 'pass' : latest.status === 'failed' ? 'fail' : 'warn'
  const finishedAt = latest.end_time || latest.start_time
  return buildCheck(
    'Pipeline status',
    status,
    `${latest.pipeline_name} is ${latest.status} (${latest.rows_processed ?? 0} rows, ${finishedAt})`
  )
}

async function getLatestMlRunCheck(
  supabase: HealthSupabaseClient
): Promise<HealthCheck> {
  const { data, error } = await supabase
    .from('ml_pipeline_runs')
    .select('run_name, status, started_at, error_count')
    .order('started_at', { ascending: false })
    .limit(1)

  if (error) return buildCheck('Latest ML run', 'fail', error.message)
  const latest = data?.[0] as
    | {
        run_name?: string
        status?: string
        started_at?: string
        error_count?: number | null
      }
    | undefined
  if (!latest) return buildCheck('Latest ML run', 'warn', 'No ML pipeline runs recorded')

  const normalizedStatus = String(latest.status).toUpperCase()
  const errors = latest.error_count ?? 0
  const status = normalizedStatus === 'SUCCESS' && errors === 0 ? 'pass' : 'fail'
  return buildCheck(
    'Latest ML run',
    status,
    `${latest.run_name} is ${latest.status} with ${errors} recorded errors (${latest.started_at})`
  )
}

async function getLatestDataQualityCheck(
  supabase: HealthSupabaseClient
): Promise<HealthCheck> {
  const { data, error } = await supabase
    .from('data_quality_results')
    .select('check_name, status, failed_rows_count, severity, created_at')
    .order('created_at', { ascending: false })
    .limit(20)

  if (error) return buildCheck('Latest data quality result', 'fail', error.message)
  const results = (data || []) as Array<{
    check_name?: string
    status?: string
    failed_rows_count?: number | null
    severity?: string | null
    created_at?: string
  }>

  if (results.length === 0) {
    return buildCheck('Latest data quality result', 'warn', 'No data quality results recorded')
  }

  const latest = results[0]
  const failing = results.filter((check) => check.status === 'fail')
  const warning = results.filter((check) => check.status === 'warning')
  const status: HealthStatus = failing.length > 0 ? 'fail' : warning.length > 0 ? 'warn' : 'pass'

  return buildCheck(
    'Latest data quality result',
    status,
    `${latest.check_name}: ${latest.status}; recent failing checks=${failing.length}, warnings=${warning.length}`,
    latest.failed_rows_count ?? 0
  )
}

function getRlsTestCheck(): HealthCheck {
  const artifact = readRlsStatusArtifact()
  if (!artifact) {
    return buildCheck(
      'RLS test status',
      'warn',
      'No cached RLS test artifact yet. Run npm run test:rls for the deep multi-tenant proof.'
    )
  }

  return buildCheck(
    'RLS test status',
    artifact.passed ? 'pass' : 'fail',
    `${artifact.passed ? 'PASS' : 'FAIL'} at ${artifact.checkedAt}; failed checks=${artifact.failedChecks}`
  )
}

async function getObservabilityChecks(
  supabase: HealthSupabaseClient
): Promise<HealthCheck[]> {
  const [
    analyticsEvents,
    failedPipelineRuns,
    failedMlRuns,
    latestMetricSnapshot,
    latestOpsInsight,
  ] = await Promise.all([
    supabase.from('analytics_events').select('*', { count: 'exact', head: true }),
    supabase.from('data_pipeline_runs').select('*', { count: 'exact', head: true }).eq('status', 'failed'),
    supabase.from('ml_pipeline_runs').select('*', { count: 'exact', head: true }).neq('status', 'SUCCESS'),
    supabase.from('metric_snapshots').select('timestamp').order('timestamp', { ascending: false }).limit(1),
    supabase.from('ops_insights').select('created_at').order('created_at', { ascending: false }).limit(1),
  ])

  const checks: HealthCheck[] = [
    buildCheck(
      'Request/event count placeholder',
      analyticsEvents.error ? 'warn' : 'pass',
      analyticsEvents.error
        ? analyticsEvents.error.message
        : 'Local analytics event count is available; this is not production APM.',
      analyticsEvents.count ?? 0
    ),
    buildCheck(
      'Failed data pipeline count',
      failedPipelineRuns.error ? 'warn' : failedPipelineRuns.count === 0 ? 'pass' : 'warn',
      failedPipelineRuns.error
        ? failedPipelineRuns.error.message
        : `${failedPipelineRuns.count ?? 0} failed data pipeline runs recorded`,
      failedPipelineRuns.count ?? 0
    ),
    buildCheck(
      'Failed ML job count',
      failedMlRuns.error ? 'warn' : failedMlRuns.count === 0 ? 'pass' : 'warn',
      failedMlRuns.error
        ? failedMlRuns.error.message
        : `${failedMlRuns.count ?? 0} non-success ML runs recorded`,
      failedMlRuns.count ?? 0
    ),
  ]

  const metricRows = (latestMetricSnapshot.data || []) as Array<{ timestamp?: string }>
  const metricTimestamp = metricRows[0]?.timestamp
  checks.push(
    buildCheck(
      'Pipeline freshness',
      metricTimestamp ? 'pass' : 'warn',
      metricTimestamp
        ? `Latest metric snapshot at ${metricTimestamp}`
        : 'No metric snapshot timestamp available'
    )
  )

  const insightRows = (latestOpsInsight.data || []) as Array<{ created_at?: string }>
  const latestInsightAt = insightRows[0]?.created_at
  checks.push(
    buildCheck(
      'Last intelligence refresh',
      latestInsightAt ? 'pass' : 'warn',
      latestInsightAt
        ? `Latest ops insight at ${latestInsightAt}`
        : 'No ops insight timestamp available'
    )
  )

  return checks
}

function summarize(checks: HealthCheck[]) {
  return checks.reduce(
    (summary, check) => {
      summary[check.status] += 1
      return summary
    },
    { pass: 0, warn: 0, fail: 0 }
  )
}

export async function getSystemHealthSnapshot(): Promise<SystemHealthSnapshot> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  const generatedAt = new Date().toISOString()

  if (!supabaseUrl || !serviceRoleKey) {
    const database = buildCheck(
      'Database connection',
      'fail',
      'Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY'
    )

    return {
      generatedAt,
      commitHash: getBuildCommitHash(),
      database,
      requiredTables: [],
      demoUsers: [],
      pipeline: buildCheck('Pipeline status', 'fail', 'Skipped because Supabase credentials are missing'),
      latestMlRun: buildCheck('Latest ML run', 'fail', 'Skipped because Supabase credentials are missing'),
      latestDataQuality: buildCheck('Latest data quality result', 'fail', 'Skipped because Supabase credentials are missing'),
      rlsTest: getRlsTestCheck(),
      observability: [],
      summary: summarize([database]),
    }
  }

  const supabase = createClient(supabaseUrl, serviceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })

  const connectionProbe = await supabase
    .from('profiles')
    .select('id', { count: 'exact', head: true })

  const database = connectionProbe.error
    ? buildCheck('Database connection', 'fail', connectionProbe.error.message)
    : buildCheck('Database connection', 'pass', 'Supabase service-role connection OK')

  const [requiredTables, demoUsers, pipeline, latestMlRun, latestDataQuality, observability] =
    await Promise.all([
      Promise.all(REQUIRED_HEALTH_TABLES.map((table) => getTableCount(supabase, table))),
      getDemoUserChecks(supabase),
      getLatestPipelineCheck(supabase),
      getLatestMlRunCheck(supabase),
      getLatestDataQualityCheck(supabase),
      getObservabilityChecks(supabase),
    ])

  const rlsTest = getRlsTestCheck()
  const allChecks = [
    database,
    ...requiredTables,
    ...demoUsers,
    pipeline,
    latestMlRun,
    latestDataQuality,
    rlsTest,
    ...observability,
  ]

  return {
    generatedAt,
    commitHash: getBuildCommitHash(),
    database,
    requiredTables,
    demoUsers,
    pipeline,
    latestMlRun,
    latestDataQuality,
    rlsTest,
    observability,
    summary: summarize(allChecks),
  }
}
