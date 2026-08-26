import React from 'react'
import { SetupRequired } from '@/components/common/SetupRequired'
import { requireAdmin } from '@/lib/auth/dal'
import {
  getSystemHealthSnapshot,
  type HealthCheck,
  type HealthStatus,
} from '@/lib/systemHealth'

/**
 * Network Executive View.
 *
 * This page previously rendered a hard-coded "HEALTHY" network status and a hard-coded
 * "DEGRADED" data-freshness status, each captioned with a source ("Provider
 * Diagnostics", "OneMove Ops Ledger") that it never queried, under a header claiming
 * "Real-time Defensible Metrics". The component performed no data fetching at all.
 *
 * Every tile below is now either derived from `getSystemHealthSnapshot()` — the same
 * probe that backs /admin/system-health — or explicitly reported as UNAVAILABLE.
 * Do not add a tile whose value is not returned by a named source.
 */

// Rendered per request: the health snapshot probes live infrastructure.
export const dynamic = 'force-dynamic'

const STATUS_LABEL: Record<HealthStatus, string> = {
  pass: 'HEALTHY',
  warn: 'DEGRADED',
  fail: 'FAILING',
}

const STATUS_CLASS: Record<HealthStatus, string> = {
  pass: 'text-emerald-400',
  warn: 'text-yellow-400',
  fail: 'text-red-400',
}

function MetricCard({
  label,
  children,
  source,
}: {
  label: string
  children: React.ReactNode
  source: string
}) {
  return (
    <div className="bg-neutral-800 p-6 rounded-lg border border-neutral-700">
      <h2 className="text-sm uppercase tracking-wider text-neutral-400 mb-1">{label}</h2>
      {children}
      <div className="text-xs text-neutral-400 mt-2">{source}</div>
    </div>
  )
}

function Unavailable({ reason }: { reason: string }) {
  return (
    <>
      <div className="text-2xl font-semibold text-neutral-400">UNAVAILABLE</div>
      <p className="text-xs text-neutral-400 mt-1">{reason}</p>
    </>
  )
}

export default async function ExecutiveDashboard() {
  if (!(await requireAdmin())) {
    return <SetupRequired />
  }

  let snapshot: Awaited<ReturnType<typeof getSystemHealthSnapshot>> | null = null
  let snapshotError: string | null = null

  try {
    snapshot = await getSystemHealthSnapshot()
  } catch (error) {
    snapshotError = error instanceof Error ? error.message : 'Health probe failed'
  }

  const overall: HealthStatus | null = snapshot
    ? snapshot.summary.fail > 0
      ? 'fail'
      : snapshot.summary.warn > 0
        ? 'warn'
        : 'pass'
    : null

  const dataQuality: HealthCheck | null = snapshot?.latestDataQuality ?? null

  return (
    <div className="min-h-screen bg-neutral-900 text-white p-8">
      <header className="mb-8 border-b border-neutral-800 pb-4">
        <h1 className="text-3xl font-bold tracking-tight">Network Executive View</h1>
        <p className="text-neutral-400 mt-2">
          System integrity, as measured by the health probe. Metrics with no connected
          source are marked UNAVAILABLE rather than estimated.
        </p>
        {snapshot && (
          <p className="text-xs text-neutral-400 mt-2">
            Snapshot generated {snapshot.generatedAt} &middot; build {snapshot.commitHash}
          </p>
        )}
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <MetricCard label="Network Status" source="Source: lib/systemHealth.ts probe">
          {overall && snapshot ? (
            <>
              <div className={`text-2xl font-semibold ${STATUS_CLASS[overall]}`}>
                {STATUS_LABEL[overall]}
              </div>
              <p className="text-xs text-neutral-400 mt-1">
                {snapshot.summary.pass} pass &middot; {snapshot.summary.warn} warn &middot;{' '}
                {snapshot.summary.fail} fail
              </p>
            </>
          ) : (
            <Unavailable reason={snapshotError ?? 'Health probe returned no snapshot.'} />
          )}
        </MetricCard>

        <MetricCard label="P95 Route Time" source="Source: not connected">
          <Unavailable reason="No routing latency metric is computed or stored by this system." />
        </MetricCard>

        <MetricCard label="Data Freshness" source="Source: data_quality_results (via health probe)">
          {dataQuality ? (
            <>
              <div className={`text-2xl font-semibold ${STATUS_CLASS[dataQuality.status]}`}>
                {STATUS_LABEL[dataQuality.status]}
              </div>
              <p className="text-xs text-neutral-400 mt-1">{dataQuality.detail}</p>
            </>
          ) : (
            <Unavailable reason={snapshotError ?? 'Health probe returned no snapshot.'} />
          )}
        </MetricCard>
      </div>

      <section className="bg-neutral-800 rounded-lg border border-neutral-700 p-6">
        <h2 className="text-xl font-semibold mb-4">Latest Decision Outcomes</h2>
        <div className="text-2xl font-semibold text-neutral-400">UNAVAILABLE</div>
        <p className="text-neutral-400 text-sm mt-1">
          No decision-outcome source is wired to this view. This panel previously asserted
          that no decisions had been frozen; nothing here queried a decision store, so that
          claim could not be made.
        </p>
      </section>
    </div>
  )
}
