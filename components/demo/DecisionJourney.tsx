'use client';

import React from 'react';

export type DemoStage =
  | 'opening'
  | 'network'
  | 'mission'
  | 'disruption'
  | 'comparison'
  | 'why'
  | 'freeze'
  | 'evidence'
  | 'replay'
  | 'closing';

export type ObjectiveComponentDelta = {
  name: string;
  raw_unit: string;
  baseline_raw_value: number;
  recommended_raw_value: number;
  solver_scaled_delta: number;
};

export type BaselineComparison = {
  status: 'AVAILABLE' | 'UNAVAILABLE';
  unavailable_reason?: string | null;
  message: string;
  evidence_class: 'DERIVED';
  baseline?: {
    baseline_id: string;
    facility_ids: string[];
    source: string;
    evidence_class: string;
  } | null;
  baseline_facility_ids: string[];
  recommended_facility_ids: string[];
  baseline_solver_objective_total?: number | null;
  recommended_solver_objective_total?: number | null;
  absolute_improvement?: number | null;
  improvement_basis_points?: number | null;
  baseline_coverage_basis_points?: number | null;
  recommended_coverage_basis_points?: number | null;
  coverage_delta_basis_points?: number | null;
  component_deltas: ObjectiveComponentDelta[];
  optimization_policy_version?: string | null;
  assumption_version?: string | null;
  graph_version?: string | null;
};

export type OptimizationScene = {
  job_id: string;
  opened_facilities: string[];
  run_duration_ms?: number | null;
  result_document: {
    status: string;
    action: string;
    assumption_version: string;
    graph_version: string;
    solver_version: string;
    problem_snapshot_id?: string;
    problem_snapshot_sha256?: string;
    evidence_ids?: string[];
    scenario_inputs: {
      scenario_id: string;
      matrix_id: string;
      graph_version: string;
      evidence_class: string;
    }[];
    objective: {
      solver_objective_total: number;
      components: {
        name: string;
        raw_unit: string;
        raw_value: number;
        solver_scaled_contribution: number;
      }[];
    };
    baseline_comparison?: BaselineComparison | null;
  };
};

export type DecisionScene = {
  decision_id: string;
  selected_action: string;
  decision_time: string;
  opened_facilities: string[];
  dataset_version: string;
  network_version: string;
  solver_version: string;
  feature_snapshot_hash: string;
  code_sha: string;
  evidence_ids: string[];
};

export type ReplayScene = {
  original_decision_id: string;
  replayed_at: string;
  pit_valid: boolean;
  expected_hash?: string | null;
  actual_hash?: string | null;
  reproduced_exact_action: boolean;
  reproduced_exact_facilities: boolean;
  objective_match: boolean;
  match_status: string;
  reason: string;
};

export type EvidenceItem = { label: string; id: string | null | undefined; evidence_class: string };

export type OperateDemoScene = {
  stage: DemoStage;
  optimization?: OptimizationScene | null;
  decision?: DecisionScene | null;
  replay?: ReplayScene | null;
  evidence?: EvidenceItem[];
};

const STORY: { stage: DemoStage; label: string }[] = [
  { stage: 'network', label: 'Operate' },
  { stage: 'mission', label: 'Mission' },
  { stage: 'disruption', label: 'Disruption' },
  { stage: 'comparison', label: 'Decision' },
  { stage: 'why', label: 'Why' },
  { stage: 'freeze', label: 'Freeze' },
  { stage: 'evidence', label: 'Evidence' },
  { stage: 'replay', label: 'Replay' },
];

const STAGE_ORDER: Record<DemoStage, number> = {
  opening: 0,
  network: 0,
  mission: 1,
  disruption: 2,
  comparison: 3,
  why: 4,
  freeze: 5,
  evidence: 6,
  replay: 7,
  closing: 8,
};

const number = (value: number | null | undefined) =>
  value == null ? 'UNAVAILABLE' : Intl.NumberFormat('en-US').format(value);

const percent = (basisPoints: number | null | undefined, signed = false) => {
  if (basisPoints == null) return 'UNAVAILABLE';
  const value = basisPoints / 100;
  return `${signed && value > 0 ? '+' : ''}${value.toFixed(1)}%`;
};

const facility = (id: string) => id.replace(/^fac:/, '');
const title = (name: string) => name.replaceAll('_', ' ');

function Badge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'pink' | 'green' | 'purple' | 'amber' }) {
  const tones = {
    neutral: 'border-slate-600/70 bg-slate-800/70 text-slate-300',
    pink: 'border-pink-500/40 bg-pink-500/10 text-pink-300',
    green: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
    purple: 'border-purple-500/40 bg-purple-500/10 text-purple-300',
    amber: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  };
  return <span className={`rounded border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${tones[tone]}`}>{children}</span>;
}

function Metric({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="border-t border-slate-800/80 py-2">
      <dt className="text-[10px] uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className={`mt-0.5 font-mono text-[13px] ${accent ? 'text-emerald-300' : 'text-slate-100'}`}>{value}</dd>
    </div>
  );
}

function FacilitySet({ ids }: { ids: string[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {ids.map((id) => (
        <span key={id} title={id} className="rounded bg-slate-800 px-1.5 py-1 font-mono text-[9px] text-slate-300">
          {facility(id)}
        </span>
      ))}
    </div>
  );
}

function Comparison({ optimization }: { optimization?: OptimizationScene | null }) {
  const comparison = optimization?.result_document.baseline_comparison;
  if (!comparison || comparison.status !== 'AVAILABLE') {
    return (
      <section data-testid="decision-comparison" className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5">
        <div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Do nothing vs recommended</h2><Badge tone="amber">UNAVAILABLE</Badge></div>
        <p className="mt-4 text-sm leading-relaxed text-slate-300">
          {comparison?.message ?? 'No incumbent facility set was supplied. No zero is substituted for a missing comparison.'}
        </p>
        <p className="mt-3 font-mono text-[10px] text-slate-500">{comparison?.unavailable_reason ?? 'NO_BASELINE_RECORDED'}</p>
      </section>
    );
  }

  const travel = comparison.component_deltas.find((item) => item.name === 'expected_travel');
  return (
    <section data-testid="decision-comparison">
      <div className="mb-4 flex items-end justify-between">
        <div><p className="text-[10px] uppercase tracking-[0.22em] text-sky-300">Same problem · snapshot · matrices · assumptions · policy</p><h2 className="mt-1 text-2xl font-semibold tracking-tight">Do nothing vs recommended</h2></div>
        <Badge>DERIVED</Badge>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <article data-testid="do-nothing" className="rounded-xl border border-pink-500/25 bg-[#0c1423]/94 p-4">
          <div className="flex items-center justify-between"><h3 className="text-sm font-semibold">DO NOTHING</h3><Badge tone="pink">SIMULATED DEMO BASELINE</Badge></div>
          <p className="mt-2 text-[11px] text-slate-400">Declared in scenario definition. Not a retailer network.</p>
          <FacilitySet ids={comparison.baseline_facility_ids} />
          <dl className="mt-3">
            <Metric label="Facility set" value={`${comparison.baseline_facility_ids.length} sites`} />
            <Metric label="Worst-scenario coverage" value={percent(comparison.baseline_coverage_basis_points)} />
            <Metric label="Expected travel load" value={number(travel?.baseline_raw_value)} />
            <Metric label="Solver objective" value={number(comparison.baseline_solver_objective_total)} />
          </dl>
        </article>
        <article data-testid="recommended" className="rounded-xl border border-emerald-500/30 bg-emerald-500/[0.06] p-4">
          <div className="flex items-center justify-between"><h3 className="text-sm font-semibold">RECOMMENDED</h3><Badge tone="green">DERIVED</Badge></div>
          <p className="mt-2 text-[11px] text-slate-400">OR-Tools CP-SAT proved optimal under the same yardstick.</p>
          <FacilitySet ids={comparison.recommended_facility_ids} />
          <dl className="mt-3">
            <Metric label="Facility set" value={`${comparison.recommended_facility_ids.length} sites`} />
            <Metric label="Worst-scenario coverage" value={percent(comparison.recommended_coverage_basis_points)} accent />
            <Metric label="Expected travel load" value={number(travel?.recommended_raw_value)} accent />
            <Metric label="Solver objective" value={number(comparison.recommended_solver_objective_total)} accent />
          </dl>
        </article>
      </div>
      <div data-testid="comparison-delta" className="mt-3 grid grid-cols-3 rounded-xl border border-sky-500/20 bg-sky-500/[0.06] px-4 py-3">
        <Metric label="Objective improvement" value={number(comparison.absolute_improvement)} accent />
        <Metric label="Relative improvement" value={percent(comparison.improvement_basis_points)} accent />
        <Metric label="Coverage delta" value={percent(comparison.coverage_delta_basis_points, true)} accent />
      </div>
    </section>
  );
}

function Why({ optimization }: { optimization?: OptimizationScene | null }) {
  const result = optimization?.result_document;
  const comparison = result?.baseline_comparison;
  const components = comparison?.component_deltas ?? [];
  const improving = [...components].filter((item) => item.solver_scaled_delta < 0).sort((a, b) => a.solver_scaled_delta - b.solver_scaled_delta)[0];
  const worsening = [...components].filter((item) => item.solver_scaled_delta > 0).sort((a, b) => b.solver_scaled_delta - a.solver_scaled_delta)[0];

  return (
    <section data-testid="why-decision">
      <div className="flex items-end justify-between"><div><p className="text-[10px] uppercase tracking-[0.22em] text-sky-300">Deterministic explanation</p><h2 className="mt-1 text-2xl font-semibold">Why this decision?</h2></div><Badge>DERIVED</Badge></div>
      <div className="mt-4 grid grid-cols-2 gap-3 text-[11px]">
        <article className="rounded-xl border border-slate-700/70 bg-[#0c1423]/94 p-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Action</p>
          <p className="mt-1 text-base font-medium text-emerald-300">{result?.action ?? 'UNAVAILABLE'}</p>
          <FacilitySet ids={optimization?.opened_facilities ?? []} />
        </article>
        <article className="rounded-xl border border-slate-700/70 bg-[#0c1423]/94 p-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Change</p>
          <p className="mt-1 text-sm text-slate-100">{comparison?.baseline_facility_ids.length ?? 'UNAVAILABLE'} baseline sites → {comparison?.recommended_facility_ids.length ?? 'UNAVAILABLE'} recommended</p>
          <p className="mt-2 text-slate-400">Coverage {percent(comparison?.coverage_delta_basis_points, true)} · objective improvement {number(comparison?.absolute_improvement)}</p>
        </article>
      </div>
      <article className="mt-3 rounded-xl border border-slate-700/70 bg-[#0c1423]/94 p-4">
        <div className="flex items-center justify-between"><h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Objective components</h3><span className="text-[10px] text-slate-500">recommendation − baseline</span></div>
        <div className="mt-2 grid grid-cols-5 gap-1.5">
          {components.map((item) => (
            <div key={item.name} className="rounded-lg bg-slate-900/80 p-2">
              <p className="truncate text-[9px] uppercase tracking-wide text-slate-500">{title(item.name)}</p>
              <p className={`mt-1 font-mono text-[11px] ${item.solver_scaled_delta <= 0 ? 'text-emerald-300' : 'text-amber-300'}`}>{item.solver_scaled_delta > 0 ? '+' : ''}{number(item.solver_scaled_delta)}</p>
            </div>
          ))}
        </div>
      </article>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <article className="rounded-xl border border-slate-700/70 bg-[#0c1423]/94 p-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Tradeoff</p>
          <p className="mt-2 text-slate-300">Largest improvement: <span className="text-emerald-300">{improving ? title(improving.name) : 'none recorded'}</span></p>
          <p className="mt-1 text-slate-300">Largest worsening: <span className="text-amber-300">{worsening ? title(worsening.name) : 'none recorded'}</span></p>
        </article>
        <article className="rounded-xl border border-slate-700/70 bg-[#0c1423]/94 p-4">
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Assumptions & evidence</p>
          <p className="mt-2 break-all font-mono text-[10px] text-slate-300">{result?.assumption_version ?? 'UNAVAILABLE'}</p>
          <p className="mt-1 text-slate-400">{result?.evidence_ids?.length ?? 0} frozen evidence references · {result?.scenario_inputs.length ?? 0} scenario matrices</p>
        </article>
      </div>
    </section>
  );
}

function Freeze({ decision }: { decision?: DecisionScene | null }) {
  return (
    <section data-testid="frozen-decision">
      <div className="flex items-center justify-between"><div><p className="text-[10px] uppercase tracking-[0.22em] text-emerald-300">Authoritative decision ledger</p><h2 className="mt-1 text-2xl font-semibold">Decision frozen</h2></div><Badge tone="green">IMMUTABLE</Badge></div>
      <dl className="mt-5 grid grid-cols-2 gap-x-6">
        <Metric label="Decision ID" value={decision?.decision_id ?? 'UNAVAILABLE'} accent />
        <Metric label="Selected action" value={decision?.selected_action ?? 'UNAVAILABLE'} />
        <Metric label="Decision time" value={decision?.decision_time ?? 'UNAVAILABLE'} />
        <Metric label="Release SHA" value={decision?.code_sha ?? 'UNAVAILABLE'} />
        <Metric label="Policy / solver" value={decision?.solver_version ?? 'UNAVAILABLE'} />
        <Metric label="Feature snapshot" value={decision?.feature_snapshot_hash ?? 'UNAVAILABLE'} />
      </dl>
      <p className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.06] p-4 text-sm leading-relaxed text-slate-300">The recommendation is now bound to its release, inputs, solver output, evidence references, and decision time.</p>
    </section>
  );
}

function Evidence({ items = [] }: { items?: EvidenceItem[] }) {
  return (
    <section data-testid="decision-evidence">
      <div className="flex items-end justify-between"><div><p className="text-[10px] uppercase tracking-[0.22em] text-sky-300">What was knowable</p><h2 className="mt-1 text-2xl font-semibold">Decision evidence</h2></div><span className="font-mono text-[10px] text-slate-500">{items.length} references</span></div>
      <ul className="mt-4 space-y-1.5">
        {items.map((item) => (
          <li key={`${item.label}-${item.id}`} className="grid grid-cols-[145px_1fr_auto] items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2.5">
            <span className="text-[11px] text-slate-400">{item.label}</span>
            <span className="truncate font-mono text-[10px] text-slate-200">{item.id || 'UNAVAILABLE'}</span>
            <Badge tone={item.evidence_class === 'SIMULATED' ? 'pink' : item.evidence_class === 'ASSUMPTION' ? 'amber' : 'neutral'}>{item.evidence_class}</Badge>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Replay({ replay }: { replay?: ReplayScene | null }) {
  const exact = replay?.match_status === 'EXACT_MATCH';
  return (
    <section data-testid="decision-replay">
      <div className="flex items-center justify-between"><div><p className="text-[10px] uppercase tracking-[0.22em] text-sky-300">Point-in-time verification</p><h2 className="mt-1 text-2xl font-semibold">Replay verdict</h2></div><Badge tone={exact ? 'green' : 'amber'}>{replay?.match_status ?? 'UNAVAILABLE'}</Badge></div>
      <div className="mt-5 grid grid-cols-3 gap-2">
        <Metric label="PIT valid" value={replay ? (replay.pit_valid ? 'YES' : 'NO') : 'UNAVAILABLE'} accent={replay?.pit_valid} />
        <Metric label="Action reproduced" value={replay ? (replay.reproduced_exact_action ? 'YES' : 'NO') : 'UNAVAILABLE'} accent={replay?.reproduced_exact_action} />
        <Metric label="Objective match" value={replay ? (replay.objective_match ? 'YES' : 'NO') : 'UNAVAILABLE'} accent={replay?.objective_match} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 font-mono text-[10px]">
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-3"><p className="mb-1 uppercase tracking-wider text-slate-500">Frozen hash</p><p className="text-slate-200">{replay?.expected_hash ?? 'UNAVAILABLE'}</p></div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-3"><p className="mb-1 uppercase tracking-wider text-slate-500">Recomputed hash</p><p className="text-slate-200">{replay?.actual_hash ?? 'UNAVAILABLE'}</p></div>
      </div>
      <p className="mt-4 rounded-xl border border-slate-700/70 bg-[#0c1423]/94 p-4 text-sm leading-relaxed text-slate-300">{replay?.reason ?? 'No replay result has been returned.'}</p>
      <p className="mt-4 text-sm leading-relaxed text-slate-400">OneMove records what was known, why the decision was made, and whether that decision can be reproduced later.</p>
    </section>
  );
}

export function DecisionJourney({ scene }: { scene: OperateDemoScene }) {
  const stage = scene.stage;
  const active = STAGE_ORDER[stage];
  return (
    <aside data-testid="decision-journey" data-demo-stage={stage} className="pointer-events-none absolute bottom-4 left-4 top-4 z-10 flex w-[650px] flex-col overflow-hidden rounded-2xl border border-slate-700/70 bg-[#070d18]/95 shadow-2xl shadow-black/50 backdrop-blur-md">
      <div className="shrink-0 border-b border-slate-800/80 px-5 py-3">
        <ol className="flex items-center justify-between gap-1" aria-label="Decision journey">
          {STORY.map((item, index) => (
            <li key={item.stage} className="flex min-w-0 flex-1 items-center gap-1">
              <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border font-mono text-[9px] ${index <= active ? 'border-sky-400/60 bg-sky-400/15 text-sky-200' : 'border-slate-700 text-slate-600'}`}>{index + 1}</span>
              <span className={`truncate text-[9px] uppercase tracking-wide ${index === active ? 'text-slate-100' : 'text-slate-600'}`}>{item.label}</span>
            </li>
          ))}
        </ol>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        {stage === 'opening' && (
          <section data-testid="demo-opening" className="flex h-full flex-col justify-center py-8">
            <Badge>OPERATE · SIMULATE · DECIDE</Badge>
            <h1 className="mt-5 max-w-lg text-5xl font-semibold leading-[1.03] tracking-[-0.04em] text-white">Physical-commerce decisions, connected.</h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-300">OneMove links geographic state, current context, uncertainty, optimization, and decision evidence in one reproducible operating surface.</p>
          </section>
        )}
        {stage === 'network' && (
          <section data-testid="network-story" className="flex h-full flex-col justify-end pb-8">
            <Badge>PUBLIC_GEOGRAPHIC</Badge><h2 className="mt-4 text-4xl font-semibold tracking-tight">Real Bengaluru context.</h2><p className="mt-4 max-w-lg text-base leading-relaxed text-slate-300">11,000+ roads and 94 canonical H3 demand zones form the pilot network. Pan, zoom, inspect layers, and read provenance directly on the map.</p>
          </section>
        )}
        {stage === 'mission' && (
          <section data-testid="mission-story" className="flex h-full flex-col justify-end pb-8">
            <Badge tone="pink">SIMULATED · 16 ORDERS</Badge><h2 className="mt-4 text-4xl font-semibold tracking-tight">A mission on real roads.</h2><p className="mt-4 max-w-lg text-base leading-relaxed text-slate-300">The orders are simulated and placed over real Bengaluru geography. They do not imply access to any retailer, customer, merchant, or rider data.</p><p className="mt-3 text-sm text-sky-300">Select an order to isolate its pickup, dropoff, and routed road geometry.</p>
          </section>
        )}
        {stage === 'disruption' && (
          <section data-testid="simulated-disruption" className="flex h-full flex-col justify-center">
            <Badge tone="purple">SIMULATED SCENARIO</Badge><h2 className="mt-4 text-4xl font-semibold tracking-tight">Facility unavailable. Congestion compounds.</h2><p className="mt-4 max-w-lg text-base leading-relaxed text-slate-300">The highlighted cell is a controlled facility-outage scenario, evaluated with the existing s3_congested_outage travel matrix. It is a counterfactual, not an observed event.</p><div className="mt-6 rounded-xl border border-purple-500/30 bg-purple-500/10 p-4"><p className="text-xs uppercase tracking-wider text-purple-300">Decision question</p><p className="mt-2 text-lg text-white">What happens if we do nothing — and what should change?</p></div>
          </section>
        )}
        {stage === 'comparison' && <Comparison optimization={scene.optimization} />}
        {stage === 'why' && <Why optimization={scene.optimization} />}
        {stage === 'freeze' && <Freeze decision={scene.decision} />}
        {stage === 'evidence' && <Evidence items={scene.evidence} />}
        {stage === 'replay' && <Replay replay={scene.replay} />}
        {stage === 'closing' && (
          <section data-testid="demo-closing" className="flex h-full flex-col justify-center py-8"><Badge tone="green">ONE DECISION RECORD</Badge><h2 className="mt-5 text-5xl font-semibold leading-[1.05] tracking-[-0.04em]">Operate. Simulate. Decide. Prove.</h2><p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-300">From real network context to a simulated mission, a derived recommendation, its evidence, and a reproducible replay.</p></section>
        )}
      </div>
    </aside>
  );
}
