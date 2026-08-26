'use client';

/**
 * What is real, stated rather than implied.
 *
 * A CTO watching a demo should never have to work out which numbers came from
 * the world and which were invented for the occasion. This panel answers that
 * for every source on screen: the provider, the evidence class, the capture
 * time, the age, and the freshness state.
 *
 * The rules it exists to enforce, all of which have been got wrong before:
 *   - UNAVAILABLE renders as UNAVAILABLE. Not a dash styled like a value, not a
 *     zero, not a neutral grey that reads as fine.
 *   - A stale reading is never labelled LIVE. The provider contract's exact
 *     freshness verdict is shown with its true age.
 *   - Geography and the mission are VERSIONED, not graded on a clock. An OSM
 *     extract does not go stale by the minute; it changes when it is recut.
 */

import React from 'react';

export type SourceContext = {
  source: string;
  provider: string | null;
  evidence_class: string;
  freshness: string;
  captured_at: string | null;
  age_seconds: number | null;
  observation_count: number;
  detail?: string | null;
  failure_count?: number;
  last_failure_at?: string | null;
  last_failure_reason?: string | null;
};

export type ZoneTraffic = {
  zone_id: string;
  /** Null means no reading. It is never 1.0-and-therefore-clear. */
  congestion_ratio: number | null;
  evidence_class: string;
  captured_at: string | null;
};

export type LiveContext = {
  as_of: string;
  capture_run_id: string | null;
  sources: SourceContext[];
  zone_traffic: ZoneTraffic[];
};

/** Colour carries meaning here, so it is defined once and never improvised. */
const FRESHNESS_TONE: Record<string, string> = {
  FRESH: 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10',
  DEGRADED: 'text-amber-300 border-amber-500/40 bg-amber-500/10',
  STALE: 'text-orange-300 border-orange-500/40 bg-orange-500/10',
  UNAVAILABLE: 'text-red-300 border-red-500/40 bg-red-500/10',
  VERSIONED: 'text-sky-300 border-sky-500/40 bg-sky-500/10',
};

const EVIDENCE_TONE: Record<string, string> = {
  PUBLIC_GEOGRAPHIC: 'text-sky-300',
  PUBLIC_OFFICIAL: 'text-emerald-300',
  PROVIDER_ESTIMATED: 'text-amber-300',
  DERIVED: 'text-violet-300',
  SIMULATED: 'text-pink-300',
  ASSUMPTION: 'text-orange-300',
};

/** Human age. `null` is not zero and must not be formatted as a duration. */
export function formatAge(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return 'no observation';
  if (seconds < 90) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 90) return `${minutes}m ago`;
  return `${(minutes / 60).toFixed(1)}h ago`;
}

/**
 * Preserve the API's closed freshness vocabulary in the UI. Friendly aliases
 * such as "current" or "recent" hide the threshold that was actually applied.
 */
export function currencyLabel(freshness: string): string {
  return freshness;
}

function SourceRow({ source }: { source: SourceContext }) {
  const unavailable = source.freshness === 'UNAVAILABLE';
  const tone = FRESHNESS_TONE[source.freshness] ?? 'text-slate-300 border-slate-600 bg-slate-800/40';

  return (
    <li
      data-source={source.source}
      data-freshness={source.freshness}
      className="border-b border-slate-800/70 py-2.5 last:border-b-0"
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[13px] font-medium text-slate-100">{source.source}</span>
        <span className={`rounded border px-1.5 py-px text-[10px] font-semibold tracking-wide ${tone}`}>
          {currencyLabel(source.freshness)}
        </span>
      </div>

      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px]">
        {source.provider && <span className="text-slate-300">{source.provider}</span>}
        <span className={EVIDENCE_TONE[source.evidence_class] ?? 'text-slate-400'}>
          {source.evidence_class}
        </span>
        <span className="text-slate-500">·</span>
        {/* Absence is spelled out. It never borrows the formatting of a value. */}
        <span className={unavailable ? 'font-medium text-red-300' : 'text-slate-400'}>
          {unavailable ? 'no observation recorded' : formatAge(source.age_seconds)}
        </span>
        {source.observation_count > 0 && (
          <>
            <span className="text-slate-500">·</span>
            <span className="text-slate-400">{source.observation_count.toLocaleString()} obs</span>
          </>
        )}
      </div>

      {(source.failure_count ?? 0) > 0 && (
        <p className="mt-1 text-[10.5px] text-orange-300/90">
          {source.failure_count} recorded outage{(source.failure_count ?? 0) === 1 ? '' : 's'}
          {source.last_failure_reason ? ` · last: ${source.last_failure_reason}` : ''}
        </p>
      )}

      {source.detail && <p className="mt-1 text-[10.5px] leading-snug text-slate-500">{source.detail}</p>}
    </li>
  );
}

export function LiveContextPanel({
  context,
  error,
  className = '',
}: {
  context: LiveContext | null;
  error?: string | null;
  className?: string;
}) {
  return (
    <section
      data-testid="live-context-panel"
      className={`rounded-xl border border-slate-700/60 bg-[#0b1220]/92 p-4 backdrop-blur ${className}`}
    >
      <div className="mb-1 flex items-baseline justify-between">
        <h2 className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">
          Live context
        </h2>
        {context?.capture_run_id && (
          <span className="font-mono text-[9.5px] text-slate-600">
            run {context.capture_run_id.slice(0, 8)}
          </span>
        )}
      </div>

      {error && (
        <p data-testid="live-context-error" className="py-3 text-[11.5px] text-red-300">
          Context unavailable: {error}. No values are substituted.
        </p>
      )}

      {!error && !context && (
        <p className="py-3 text-[11.5px] text-slate-500">Reading observation store…</p>
      )}

      {context && (
        <ul className="mt-1">
          {context.sources.map((source) => (
            <SourceRow key={source.source} source={source} />
          ))}
        </ul>
      )}
    </section>
  );
}
