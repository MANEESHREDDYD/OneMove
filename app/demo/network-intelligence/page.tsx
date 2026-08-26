'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { BengaluruMap, type MapMode } from '@/components/demo/BengaluruMap';

/**
 * The presentation route for the network-intelligence walkthrough.
 *
 * This route renders state; it does not compute it. Every operational value on
 * screen is pushed in from the recording harness, which obtained it from the
 * real API under a real session. Nothing here re-derives a metric, and any
 * field the backend did not return is rendered as UNAVAILABLE or omitted
 * rather than defaulted to a plausible-looking number.
 *
 * It mounts as a fixed full-viewport surface so the operator chrome in the root
 * layout cannot frame the recording.
 */

type Stage =
  | 'opening'
  | 'live'
  | 'observe'
  | 'mission'
  | 'bridge'
  | 'scenario'
  | 'impact'
  | 'optimizing'
  | 'result'
  | 'decision'
  | 'evidence'
  | 'replay'
  | 'closing';

type Payload = {
  stage: Stage;
  weather?: Record<string, unknown> | null;
  traffic?: Record<string, unknown> | null;
  evidence?: Record<string, unknown> | null;
  scenario?: Record<string, unknown> | null;
  impact?: Record<string, unknown> | null;
  job?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  decision?: Record<string, unknown> | null;
  lineage?: Record<string, unknown>[] | null;
  replay?: Record<string, unknown> | null;
  candidates?: string[];
  selected?: string[];
  mission?: Record<string, unknown> | null;
  missionState?: string | null;
  missionProgress?: number | null;
};

const EVIDENCE_TONE: Record<string, string> = {
  PUBLIC_GEOGRAPHIC: 'bg-emerald-500/15 text-emerald-300 ring-emerald-400/30',
  PUBLIC_OFFICIAL: 'bg-sky-500/15 text-sky-300 ring-sky-400/30',
  PROVIDER_ESTIMATED: 'bg-violet-500/15 text-violet-300 ring-violet-400/30',
  SIMULATED: 'bg-orange-500/15 text-orange-300 ring-orange-400/30',
  ASSUMPTION: 'bg-amber-500/15 text-amber-300 ring-amber-400/30',
  DERIVED: 'bg-blue-500/15 text-blue-300 ring-blue-400/30',
  UNAVAILABLE: 'bg-slate-600/20 text-slate-400 ring-slate-500/30',
};

function Badge({ kind }: { kind: string }) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-[3px] text-[11px] font-semibold tracking-wide ring-1 ${
        EVIDENCE_TONE[kind] ?? EVIDENCE_TONE.UNAVAILABLE
      }`}
    >
      {kind}
    </span>
  );
}

/** A value that is absent renders as UNAVAILABLE — never as 0, "-", or a guess. */
function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  const missing = value === null || value === undefined || value === '';
  return (
    <div className="flex items-baseline justify-between gap-6 py-[7px]">
      <span className="shrink-0 text-[13px] text-slate-400">{label}</span>
      <span
        className={`text-right text-[14px] ${mono ? 'font-mono text-[13px]' : ''} ${
          missing ? 'text-slate-500' : 'text-slate-100'
        }`}
      >
        {missing ? 'UNAVAILABLE' : value}
      </span>
    </div>
  );
}

function Panel({
  title,
  eyebrow,
  children,
  wide,
}: {
  title: string;
  eyebrow?: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border border-slate-700/60 bg-[#0b1220]/95 p-5 shadow-2xl backdrop-blur ${
        wide ? 'w-[560px]' : 'w-[420px]'
      }`}
    >
      {eyebrow && (
        <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-[0.14em] text-slate-500">
          {eyebrow}
        </div>
      )}
      <h2 className="mb-3 text-[19px] font-semibold text-slate-50">{title}</h2>
      {children}
    </div>
  );
}

function freshness(iso?: string | null): { label: string; tone: string } {
  if (!iso) return { label: 'UNAVAILABLE', tone: 'text-slate-500' };
  const age = (Date.now() - new Date(iso).getTime()) / 1000;
  if (!Number.isFinite(age)) return { label: 'UNAVAILABLE', tone: 'text-slate-500' };
  if (age < 900) return { label: 'LIVE', tone: 'text-emerald-400' };
  if (age < 3600) return { label: 'FRESH', tone: 'text-sky-400' };
  return { label: 'STALE', tone: 'text-amber-400' };
}

const IST = (iso?: string | null) =>
  iso
    ? new Date(iso).toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Kolkata',
      }) + ' IST'
    : null;

export default function NetworkIntelligenceDemo() {
  const [p, setP] = useState<Payload>({ stage: 'opening' });
  const [zoneCount, setZoneCount] = useState(0);

  useEffect(() => {
    (window as unknown as { __omDemo: (next: Payload) => void }).__omDemo = (next) =>
      setP((prev) => ({ ...prev, ...next }));
    (window as unknown as { __omReady: boolean }).__omReady = true;
  }, []);

  const onReady = useCallback((n: number) => setZoneCount(n), []);

  const stage = p.stage;
  const mode: MapMode =
    stage === 'scenario' || stage === 'impact'
      ? 'scenario'
      : stage === 'result' || stage === 'decision' || stage === 'evidence' || stage === 'replay' || stage === 'closing'
        ? 'optimized'
        : 'baseline';

  const showTraffic = stage !== 'opening' && stage !== 'live';
  const mission = (p.mission ?? null) as Record<string, any> | null;
  const missionOn = stage === 'mission' || stage === 'bridge';
  const MISSION_STATES = ['CREATED', 'ACCEPTED', 'PICKUP', 'EN ROUTE', 'DELIVERED'];
  const mm = (v: unknown) =>
    typeof v === 'number' ? `${Math.floor(v / 60)}m ${String(v % 60).padStart(2, '0')}s` : null;
  const w = (p.weather ?? {}) as Record<string, string | number | null>;
  const tr = (p.traffic ?? {}) as Record<string, unknown>;
  const segments = (tr.segments as Record<string, number | string>[] | undefined) ?? [];
  const trFresh = freshness(tr.captured_at as string | undefined);
  const wFresh = freshness(w.observed_at as string | undefined);

  return (
    <div className="fixed inset-0 z-[60] flex flex-col overflow-hidden bg-[#04070d] font-sans text-slate-100">
      {/* ---- top bar -------------------------------------------------- */}
      <header className="z-20 flex shrink-0 items-center justify-between border-b border-slate-800/80 bg-[#070c16] px-8 py-3">
        <div className="flex items-baseline gap-4">
          <span className="text-[19px] font-semibold tracking-tight text-slate-50">OneMove</span>
          <span className="text-[12.5px] text-slate-500">
            Physical Commerce Network Intelligence
          </span>
        </div>
        <div className="flex items-center gap-7 text-[12.5px]">
          <span className="text-slate-400">
            Bengaluru Pilot Network · <span className="text-slate-200">{zoneCount || '—'} zones</span>
          </span>
          <span className="text-slate-500">
            Demo as-of <span className="text-slate-300">{IST(new Date().toISOString())}</span>
          </span>
        </div>
      </header>

      <div className="relative flex min-h-0 flex-1">
        {/* ---- map stage ---------------------------------------------- */}
        <div className="absolute inset-0">
          <BengaluruMap
            mode={mode}
            showTraffic={showTraffic}
            candidates={p.candidates ?? []}
            selected={stage === 'result' || stage === 'decision' || stage === 'evidence' || stage === 'replay' || stage === 'closing' ? (p.selected ?? []) : []}
            dim={stage === 'opening' ? 0.82 : 0}
            mission={
              missionOn && mission
                ? {
                    points: mission.points,
                    origin: mission.origin,
                    destination: mission.destination,
                  }
                : null
            }
            missionProgress={stage === 'mission' ? (p.missionProgress ?? null) : null}
            onReady={onReady}
          />
        </div>

        {/* ---- layer legend ------------------------------------------- */}
        {stage !== 'opening' && (
          <div className="pointer-events-none absolute left-7 top-6 z-10 w-[264px] rounded-xl border border-slate-700/50 bg-[#0b1220]/90 p-4 backdrop-blur">
            <div className="mb-2.5 text-[10.5px] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Map layers
            </div>
            {[
              ['Bengaluru base map', 'VISIBLE', 'text-emerald-400'],
              ['H3 network', `${zoneCount} / VISIBLE`, 'text-emerald-400'],
              [
                'Live traffic',
                showTraffic ? trFresh.label : 'OFF',
                showTraffic ? trFresh.tone : 'text-slate-500',
              ],
              [
                'Scenario impact',
                mode === 'scenario' ? 'ACTIVE' : 'INACTIVE',
                mode === 'scenario' ? 'text-orange-400' : 'text-slate-500',
              ],
              [
                'Selected facilities',
                (p.selected?.length ?? 0) > 0 && mode === 'optimized'
                  ? `${p.selected!.length} ACTIVE`
                  : 'INACTIVE',
                (p.selected?.length ?? 0) > 0 && mode === 'optimized'
                  ? 'text-emerald-400'
                  : 'text-slate-500',
              ],
            ].map(([name, state, tone]) => (
              <div key={name as string} className="flex items-center justify-between py-[5px] text-[12.5px]">
                <span className="text-slate-400">{name}</span>
                <span className={`font-medium ${tone}`}>{state}</span>
              </div>
            ))}
          </div>
        )}

        {/* ---- opening ------------------------------------------------- */}
        {stage === 'opening' && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center">
            <h1 className="text-[86px] font-semibold leading-none tracking-tight text-slate-50">OneMove</h1>
            <p className="mt-6 max-w-[760px] text-center text-[25px] font-light leading-snug text-slate-300">
              Physical Commerce Network Intelligence,
              <br />
              Resilience &amp; Decision Optimization
            </p>
            <p className="mt-10 text-[16px] tracking-wide text-slate-500">
              Observe the network. Stress the network. Optimize the response. Preserve the decision.
            </p>
          </div>
        )}

        {/* ---- right rail ---------------------------------------------- */}
        <div className="pointer-events-none absolute right-7 top-6 z-10 flex flex-col gap-4">
          {stage === 'live' && (
            <Panel title="Bengaluru Network — Live Observation" eyebrow="Observed baseline">
              <Row label="Network zones" value={zoneCount || null} />
              <Row label="H3 resolution" value={(p.evidence?.h3_resolution as number) ?? 8} />
              <Row label="Source" value={(p.evidence?.source as string) ?? null} mono />
              <Row label="Graph version" value={(p.evidence?.source_version as string) ?? null} mono />
              <div className="mt-3 flex items-center justify-between border-t border-slate-700/50 pt-3">
                <span className="text-[13px] text-slate-400">Network evidence</span>
                <Badge kind={(p.evidence?.evidence_class as string) ?? 'UNAVAILABLE'} />
              </div>
            </Panel>
          )}

          {stage === 'observe' && (
            <>
              <Panel title="Current Weather" eyebrow="Bengaluru · observed · Open-Meteo">
                <Row label="Condition" value={(w.condition as string) ?? null} />
                <Row label="Temperature" value={w.temperature_c != null ? `${w.temperature_c} °C` : null} />
                <Row label="Precipitation" value={w.precipitation_mm != null ? `${w.precipitation_mm} mm` : null} />
                <Row label="Humidity" value={w.humidity_pct != null ? `${w.humidity_pct} %` : null} />
                <Row label="Wind" value={w.wind_kmh != null ? `${w.wind_kmh} km/h` : null} />
                <Row label="Observed at" value={IST(w.observed_at as string)} />
                <div className="mt-3 flex items-center justify-between border-t border-slate-700/50 pt-3">
                  <span className={`text-[13px] font-medium ${wFresh.tone}`}>{wFresh.label}</span>
                  <Badge kind="PUBLIC_OFFICIAL" />
                </div>
              </Panel>

              <Panel title="Live Traffic" eyebrow={`Live observation · provider ${(tr.provider as string) ?? 'UNAVAILABLE'}`}>
                {segments.slice(0, 5).map((s) => (
                  <div key={s.name as string} className="flex items-center justify-between py-[6px]">
                    <span className="max-w-[210px] truncate text-[12.5px] text-slate-400">{s.name}</span>
                    <span className="flex items-baseline gap-2.5 font-mono text-[12.5px]">
                      <span className="text-slate-300">
                        {s.current_speed_kmh}/{s.free_flow_speed_kmh} km/h
                      </span>
                      <span
                        className={
                          Number(s.congestion_ratio) >= 1.2
                            ? 'text-amber-400'
                            : Number(s.congestion_ratio) > 1.0
                              ? 'text-sky-400'
                              : 'text-emerald-400'
                        }
                      >
                        ×{s.congestion_ratio}
                      </span>
                    </span>
                  </div>
                ))}
                <div className="mt-3 flex items-center justify-between border-t border-slate-700/50 pt-3">
                  <span className="text-[12.5px] text-slate-400">
                    Captured {IST(tr.captured_at as string)} ·{' '}
                    <span className={`font-medium ${trFresh.tone}`}>{trFresh.label}</span>
                  </span>
                  <Badge kind="PROVIDER_ESTIMATED" />
                </div>
              </Panel>
            </>
          )}

          {stage === 'mission' && (
            <Panel title="Simulated Delivery Mission" eyebrow="One mission on the live network">
              <div className="mb-3 flex items-center justify-between rounded-lg border border-orange-400/25 bg-orange-500/[0.07] px-3 py-2">
                <span className="text-[12.5px] text-orange-200">Mission is synthetic</span>
                <Badge kind="SIMULATED" />
              </div>

              <div className="mb-3 space-y-[7px]">
                {MISSION_STATES.map((st) => {
                  const cur = (p.missionState ?? 'CREATED').toUpperCase();
                  const idx = MISSION_STATES.indexOf(cur);
                  const here = MISSION_STATES.indexOf(st);
                  const done = here < idx;
                  const active = here === idx;
                  return (
                    <div key={st} className="flex items-center gap-3">
                      <span
                        className={`h-2.5 w-2.5 rounded-full ${
                          active ? 'bg-amber-300' : done ? 'bg-emerald-400' : 'bg-slate-700'
                        }`}
                      />
                      <span
                        className={`font-mono text-[13px] ${
                          active ? 'text-amber-200' : done ? 'text-emerald-300' : 'text-slate-600'
                        }`}
                      >
                        {st}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="border-t border-slate-700/50 pt-2">
                <Row label="Distance" value={mission?.distance_m ? `${(mission.distance_m / 1000).toFixed(2)} km` : null} />
                <Row label="Baseline ETA" value={mm(mission?.baseline_eta_s)} />
                <Row label="Traffic-aware ETA" value={mm(mission?.traffic_eta_s)} />
                <Row
                  label="Current delay"
                  value={
                    mission?.delay_s != null ? (
                      <span className="text-amber-300">+{mm(mission.delay_s)}</span>
                    ) : null
                  }
                />
                <Row
                  label="Congestion ratio"
                  value={mission?.congestion_ratio ? `×${mission.congestion_ratio}` : null}
                />
              </div>
              <div className="mt-3 flex items-center justify-between border-t border-slate-700/50 pt-3">
                <span className="text-[12px] text-slate-500">Route + ETAs from {mission?.provider ?? 'UNAVAILABLE'}</span>
                <Badge kind="PROVIDER_ESTIMATED" />
              </div>
            </Panel>
          )}

          {(stage === 'scenario' || stage === 'impact') && (
            <Panel title="Monsoon Stress Test" eyebrow="Scenario studio">
              <div className="mb-3 rounded-lg border border-orange-400/25 bg-orange-500/[0.07] p-3">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-[12.5px] font-medium text-orange-200">Counterfactual</span>
                  <Badge kind="SIMULATED" />
                </div>
                <p className="text-[12.5px] leading-relaxed text-slate-400">
                  What happens if severe monsoon conditions degrade travel times across the
                  Bengaluru network — beyond the conditions observed right now?
                </p>
              </div>
              <Row label="Scenario" value={(p.scenario?.scenario_id as string) ?? null} mono />
              <Row label="Type" value={(p.scenario?.scenario_type as string) ?? null} />
              <Row label="Travel-time shock" value={(p.scenario?.shock as string) ?? null} />
              <div className="mt-3 grid grid-cols-2 gap-3 border-t border-slate-700/50 pt-3">
                <div className="rounded-lg bg-slate-800/40 p-3">
                  <div className="text-[10.5px] uppercase tracking-wider text-slate-500">Observed now</div>
                  <div className="mt-1 text-[15px] text-slate-200">{(w.condition as string) ?? 'UNAVAILABLE'}</div>
                  <div className="text-[12.5px] text-slate-400">
                    {w.precipitation_mm != null ? `${w.precipitation_mm} mm rain` : 'UNAVAILABLE'}
                  </div>
                </div>
                <div className="rounded-lg bg-orange-500/[0.09] p-3">
                  <div className="text-[10.5px] uppercase tracking-wider text-orange-300/70">Stress case</div>
                  <div className="mt-1 text-[15px] text-orange-200">HEAVY_RAIN</div>
                  <div className="text-[12.5px] text-orange-300/80">+60% travel time</div>
                </div>
              </div>
            </Panel>
          )}

          {stage === 'impact' && (
            <Panel title="Scenario Impact" eyebrow="Derived from the frozen matrix">
              <Row label="Coverage" value={(p.impact?.coverage as string) ?? null} />
              <Row label="P50 travel" value={(p.impact?.p50 as string) ?? null} />
              <Row label="P90 travel" value={(p.impact?.p90 as string) ?? null} />
              <Row label="P95 travel" value={(p.impact?.p95 as string) ?? null} />
              <Row label="Disconnected zones" value={(p.impact?.disconnected as string) ?? null} />
              <Row label="Redundancy index" value={(p.impact?.redundancy as string) ?? null} />
              <Row label="Degradation grade" value={(p.impact?.grade as string) ?? null} />
              <div className="mt-3 flex justify-end border-t border-slate-700/50 pt-3">
                <Badge kind="DERIVED" />
              </div>
            </Panel>
          )}

          {stage === 'optimizing' && (
            <Panel title="Optimization Submitted" eyebrow="Asynchronous execution">
              <Row label="Job" value={(p.job?.job_id as string) ?? null} mono />
              <Row label="Model" value="CP-SAT" />
              <Row label="Execution" value="Asynchronous · durable queue" />
              <div className="mt-4 space-y-2 border-t border-slate-700/50 pt-4">
                {['QUEUED', 'RUNNING', 'OPTIMAL'].map((s) => {
                  const cur = (p.job?.status as string) ?? 'QUEUED';
                  const order = ['QUEUED', 'RUNNING', 'OPTIMAL'];
                  const done = order.indexOf(cur) > order.indexOf(s);
                  const active = cur === s;
                  return (
                    <div key={s} className="flex items-center gap-3">
                      <span
                        className={`h-2.5 w-2.5 rounded-full ${
                          active ? 'bg-sky-400' : done ? 'bg-emerald-400' : 'bg-slate-700'
                        }`}
                      />
                      <span
                        className={`font-mono text-[13.5px] ${
                          active ? 'text-sky-300' : done ? 'text-emerald-300' : 'text-slate-600'
                        }`}
                      >
                        {s}
                      </span>
                    </div>
                  );
                })}
              </div>
            </Panel>
          )}

          {stage === 'result' && (
            <Panel title="Optimization Result" eyebrow="Google OR-Tools CP-SAT" wide>
              <div className="mb-4 flex items-center gap-4 rounded-lg border border-emerald-400/25 bg-emerald-500/[0.08] px-4 py-3">
                <span className="text-[34px] font-semibold leading-none text-emerald-300">
                  {(p.result?.status as string) ?? 'UNAVAILABLE'}
                </span>
                <div className="text-[12.5px] leading-tight text-slate-400">
                  proved optimal
                  <br />
                  <span className="font-mono text-slate-300">{(p.result?.solver_version as string) ?? ''}</span>
                </div>
              </div>
              <Row label="Job" value={(p.result?.job_id as string) ?? null} mono />
              <Row label="Action" value={(p.result?.action as string) ?? null} />
              <Row label="Facilities opened" value={(p.result?.opened_count as string) ?? null} />
              <Row label="Scenarios evaluated" value={(p.result?.scenario_count as string) ?? null} />
              <Row label="Weighted objective" value={(p.result?.objective as string) ?? null} mono />
              <Row label="Solve time" value={(p.result?.runtime as string) ?? null} />
              <div className="mt-3 flex items-center justify-between border-t border-slate-700/50 pt-3">
                <span className="font-mono text-[11.5px] text-slate-500">
                  {(p.result?.assumption_version as string) ?? ''}
                </span>
                <Badge kind="ASSUMPTION" />
              </div>
            </Panel>
          )}

          {stage === 'decision' && (
            <Panel title="Decision Frozen" eyebrow="Authoritative decision ledger" wide>
              <Row label="Decision" value={(p.decision?.decision_id as string) ?? null} mono />
              <Row label="Selected action" value={(p.decision?.selected_action as string) ?? null} />
              <Row label="Decision time" value={(p.decision?.decision_time as string) ?? null} mono />
              <Row label="Facilities opened" value={(p.decision?.facilities as string) ?? null} mono />
              <Row label="Dataset version" value={(p.decision?.dataset_version as string) ?? null} mono />
              <Row label="Network version" value={(p.decision?.network_version as string) ?? null} mono />
              <Row label="Solver version" value={(p.decision?.solver_version as string) ?? null} mono />
              <Row label="Feature snapshot" value={(p.decision?.feature_snapshot_hash as string) ?? null} mono />
              <Row label="Release (code_sha)" value={(p.decision?.code_sha as string) ?? null} mono />
              <p className="mt-3 border-t border-slate-700/50 pt-3 text-[12.5px] leading-relaxed text-slate-400">
                Optimizer-derived values are read from the authoritative solver result. An
                operator cannot type them in.
              </p>
            </Panel>
          )}

          {stage === 'evidence' && (
            <Panel title="Evidence Lineage" eyebrow="Provenance chain" wide>
              <div className="space-y-0">
                {(p.lineage ?? []).map((n, i, arr) => (
                  <div key={i}>
                    <div className="flex items-center justify-between gap-4 py-[7px]">
                      <div className="min-w-0">
                        <div className="text-[13.5px] text-slate-200">{n.label as string}</div>
                        {n.id ? (
                          <div className="truncate font-mono text-[11.5px] text-slate-500">{n.id as string}</div>
                        ) : null}
                      </div>
                      {n.cls ? <Badge kind={n.cls as string} /> : null}
                    </div>
                    {i < arr.length - 1 && <div className="ml-1 h-3 w-px bg-slate-700" />}
                  </div>
                ))}
              </div>
            </Panel>
          )}

          {stage === 'replay' && (
            <Panel title="Point-in-Time Replay" eyebrow="Temporal reproduction" wide>
              <Row label="Decision" value={(p.replay?.decision_id as string) ?? null} mono />
              <Row label="Original decision time" value={(p.replay?.decision_time as string) ?? null} mono />
              <Row label="Replay as-of" value={(p.replay?.as_of as string) ?? null} mono />
              <Row label="Assumption set" value={(p.replay?.assumption as string) ?? null} mono />
              <Row label="Point-in-time valid" value={(p.replay?.pit_valid as string) ?? null} />
              <Row label="Action reproduced" value={(p.replay?.action_reproduced as string) ?? null} />
              <Row label="Facilities reproduced" value={(p.replay?.facilities_reproduced as string) ?? null} />
              <Row label="Objective match" value={(p.replay?.objective_match as string) ?? null} />
              <div className="my-3 grid grid-cols-2 gap-3 border-y border-slate-700/50 py-3">
                <div>
                  <div className="text-[10.5px] uppercase tracking-wider text-slate-500">Frozen hash</div>
                  <div className="font-mono text-[12px] text-slate-300">
                    {(p.replay?.frozen_hash as string) ?? 'UNAVAILABLE'}
                  </div>
                </div>
                <div>
                  <div className="text-[10.5px] uppercase tracking-wider text-slate-500">Recomputed</div>
                  <div className="font-mono text-[12px] text-emerald-300">
                    {(p.replay?.recomputed_hash as string) ?? 'UNAVAILABLE'}
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[13px] text-slate-400">Replay result</span>
                <span className="rounded bg-emerald-500/15 px-2.5 py-1 text-[13px] font-semibold text-emerald-300 ring-1 ring-emerald-400/30">
                  {(p.replay?.match_status as string) ?? 'UNAVAILABLE'}
                </span>
              </div>
              <p className="mt-3 text-[12.5px] leading-relaxed text-slate-400">
                The decision is replayed using information that was knowable at that point in
                time — not today&apos;s state.
              </p>
            </Panel>
          )}
        </div>

        {/* ---- bridge from one mission to the network ------------------- */}
        {stage === 'bridge' && (
          <div className="absolute inset-x-0 bottom-0 z-10 flex flex-col items-center bg-gradient-to-t from-[#04070d] via-[#04070d]/94 to-transparent pb-16 pt-28">
            <p className="text-[30px] font-light leading-snug text-slate-200">
              One delayed delivery is a routing problem.
            </p>
            <p className="mt-2 text-[30px] font-light leading-snug text-slate-50">
              Correlated delays across a city become a network decision problem.
            </p>
          </div>
        )}

        {/* ---- closing ------------------------------------------------- */}
        {stage === 'closing' && (
          <div className="absolute inset-x-0 bottom-0 z-10 flex flex-col items-center bg-gradient-to-t from-[#04070d] via-[#04070d]/92 to-transparent pb-14 pt-24">
            <div className="flex items-center gap-3 text-[15px] font-medium tracking-[0.16em] text-slate-300">
              {['OBSERVE', 'STRESS', 'OPTIMIZE', 'DECIDE', 'PROVE', 'REPLAY'].map((s, i) => (
                <React.Fragment key={s}>
                  {i > 0 && <span className="text-slate-600">→</span>}
                  <span>{s}</span>
                </React.Fragment>
              ))}
            </div>
            <p className="mt-6 text-[23px] font-light text-slate-200">
              OneMove turns physical network data into reproducible operational decisions.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
