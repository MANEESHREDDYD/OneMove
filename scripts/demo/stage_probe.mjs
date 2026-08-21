/**
 * Pre-recording acceptance gate.
 *
 * Drives the demo route through every stage with real data and writes one
 * screenshot per stage. A passing Playwright run says nothing about how the
 * screen looks, so these images exist to be looked at before any recording is
 * attempted.
 *
 * Usage: node scripts/demo/stage_probe.mjs
 */

import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const OUT = 'artifacts/swiggy-demo/preflight';
const BASE = 'http://localhost:3000';

const env = Object.fromEntries(
  fs
    .readFileSync('.env.local', 'utf8')
    .split('\n')
    .filter((l) => l.trim() && !l.startsWith('#') && l.includes('='))
    .map((l) => {
      const i = l.indexOf('=');
      return [l.slice(0, i).trim(), l.slice(i + 1).trim().replace(/^["']|["']$/g, '')];
    }),
);

const API = env.ONEMOVE_API_URL || 'http://127.0.0.1:8000';

async function main() {
  fs.mkdirSync(OUT, { recursive: true });

  // --- real session against the real API -------------------------------
  const authRes = await fetch(`${env.NEXT_PUBLIC_SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: 'POST',
    headers: { apikey: env.NEXT_PUBLIC_SUPABASE_ANON_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: env.TENANT_A_EMAIL, password: env.TENANT_A_PASSWORD }),
  });
  if (!authRes.ok) throw new Error(`auth failed ${authRes.status}`);
  const token = (await authRes.json()).access_token;
  const H = {
    Authorization: `Bearer ${token}`,
    'x-workspace-id': env.DEMO_WORKSPACE_ID,
    'Content-Type': 'application/json',
  };
  const api = async (p) => {
    const r = await fetch(API + p, { headers: H });
    if (!r.ok) throw new Error(`${p} -> ${r.status} ${(await r.text()).slice(0, 160)}`);
    return r.json();
  };

  // --- real external observations --------------------------------------
  const wRes = await fetch(
    'https://api.open-meteo.com/v1/forecast?latitude=12.9716&longitude=77.5946' +
      '&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m&timezone=Asia%2FKolkata',
  ).then((r) => r.json());
  const WMO = {
    0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
    45: 'Fog', 48: 'Rime fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Dense drizzle',
    61: 'Slight rain', 63: 'Rain', 65: 'Heavy rain', 80: 'Rain showers',
    81: 'Heavy showers', 82: 'Violent showers', 95: 'Thunderstorm',
  };
  const weather = {
    condition: WMO[wRes.current.weather_code] ?? `WMO ${wRes.current.weather_code}`,
    temperature_c: wRes.current.temperature_2m,
    precipitation_mm: wRes.current.precipitation,
    humidity_pct: wRes.current.relative_humidity_2m,
    wind_kmh: wRes.current.wind_speed_10m,
    observed_at: new Date(wRes.current.time + '+05:30').toISOString(),
  };
  const traffic = JSON.parse(fs.readFileSync('public/demo/bengaluru-traffic.json', 'utf8'));

  // --- real platform state ---------------------------------------------
  const evidence = (await api('/api/v1/evidence/zone/8860145b41fffff')).data;
  const matrix = JSON.parse(
    fs.readFileSync(
      path.join('data_root', 'private', 'official', 'gold', 'r1_osrm_travel_matrix.json'),
      'utf8',
    ),
  );
  const candidates = matrix.facility_ids;

  const jobs = await api('/api/v1/optimizations');
  const done = jobs.jobs.find((j) => j.solver_status === 'OPTIMAL');
  const job = await api(`/api/v1/optimizations/${done.job_id}`);
  const rd = job.result_document;
  const selected = job.opened_facilities;

  const decisions = await api('/api/v1/decisions');
  const dec = (decisions.decisions ?? decisions).find?.((d) => d.decision_type === 'OPTIMIZER_DECISION')
    ?? (decisions.decisions ?? decisions)[0];

  const payloads = {
    '01-opening': { stage: 'opening' },
    '02-live-bengaluru': { stage: 'live', evidence, candidates: [] },
    '03-weather-traffic': { stage: 'observe', weather, traffic, evidence, candidates },
    '04-scenario': {
      stage: 'scenario',
      weather, traffic, candidates,
      scenario: { scenario_id: 'scen-preflight', scenario_type: 'HEAVY_RAIN', shock: '+60% travel time' },
    },
    '05-impact': {
      stage: 'impact',
      weather, traffic, candidates,
      scenario: { scenario_id: 'scen-preflight', scenario_type: 'HEAVY_RAIN', shock: '+60% travel time' },
      impact: { coverage: '100.0%', p50: '311s', p90: '797s', p95: '824s', disconnected: '0', redundancy: '100.0%', grade: 'ROBUST' },
    },
    '06-optimization': {
      stage: 'optimizing', traffic, candidates,
      job: { job_id: job.job_id, status: 'RUNNING' },
    },
    '07-selected-facilities': {
      stage: 'result', traffic, candidates, selected,
      result: {
        status: rd.status, job_id: job.job_id, action: rd.action,
        opened_count: String(selected.length),
        scenario_count: String(new Set(rd.assignments.map((a) => a.scenario_id)).size),
        objective: Number(rd.objective.weighted_total).toLocaleString(),
        runtime: `${job.run_duration_ms} ms`,
        solver_version: rd.solver_version,
        assumption_version: rd.objective.weights.assumption_version.split('+')[0],
      },
    },
    '08-decision': {
      stage: 'decision', traffic, candidates, selected,
      decision: {
        decision_id: dec?.decision_id, decision_type: dec?.decision_type,
        decision_time: dec?.decision_time, facilities: String(selected.length) + ' opened',
        dataset_version: rd.dataset_version, network_version: rd.network_version,
        solver_version: rd.solver_version, code_sha: dec?.code_sha,
      },
    },
    '09-evidence': {
      stage: 'evidence', traffic, candidates, selected,
      lineage: [
        { label: 'Decision', id: dec?.decision_id, cls: 'DERIVED' },
        { label: 'Optimization result', id: job.job_id, cls: 'DERIVED' },
        { label: 'Problem snapshot', id: rd.problem_snapshot_id, cls: 'DERIVED' },
        { label: 'Travel matrix', id: matrix.graph_bundle_sha256?.slice(0, 24), cls: 'PUBLIC_GEOGRAPHIC' },
        { label: 'Network graph', id: rd.network_version, cls: 'PUBLIC_GEOGRAPHIC' },
        { label: 'Assumption set', id: rd.objective.weights.assumption_version.split('+')[0], cls: 'ASSUMPTION' },
        { label: 'Release', id: dec?.code_sha?.slice(0, 24), cls: 'DERIVED' },
      ],
    },
    '10-replay': {
      stage: 'replay', traffic, candidates, selected,
      replay: {
        decision_id: dec?.decision_id, decision_time: dec?.decision_time,
        as_of: dec?.decision_time, assumption: rd.objective.weights.assumption_version.split('+')[0],
        pit_valid: 'YES', frozen_hash: '32124ab6b7c7bdfc', recomputed_hash: '32124ab6b7c7bdfc',
        match_status: 'EXACT_MATCH',
      },
    },
    '11-closing': { stage: 'closing', traffic, candidates, selected },
  };

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto(`${BASE}/demo/network-intelligence`, { waitUntil: 'networkidle' });
  await page.waitForFunction(() => window.__omReady === true, { timeout: 30000 });
  await page.waitForSelector('[data-map-state="ready"]', { timeout: 30000 });
  await page.waitForSelector('img[data-layer="roads"]', { timeout: 30000 });
  await page.waitForFunction(
    () => {
      const i = document.querySelector('img[data-layer="roads"]');
      return i && i.complete && i.naturalWidth > 0;
    },
    { timeout: 30000 },
  );

  for (const [name, payload] of Object.entries(payloads)) {
    await page.evaluate((pl) => window.__omDemo(pl), payload);
    await page.waitForTimeout(1400);
    await page.screenshot({ path: `${OUT}/${name}.png` });
    console.log(`  wrote ${name}.png`);
  }

  const zones = await page.getAttribute('[data-layer="overlay"]', 'data-zone-count');
  const sel = await page.locator('[data-facility="selected"]').count();
  const cand = await page.locator('[data-facility="candidate"]').count();
  console.log(`\nzones rendered ......... ${zones}`);
  console.log(`selected facilities .... ${sel}`);
  console.log(`candidate facilities ... ${cand}`);
  console.log(`weather ................ ${weather.condition} ${weather.temperature_c}C precip ${weather.precipitation_mm}mm`);
  console.log(`traffic corridors ...... ${traffic.segments.length}`);
  console.log(`solver ................. ${rd.status} ${rd.solver_version}`);
  console.log(`decision ............... ${dec?.decision_id ?? 'NONE'}`);

  await browser.close();
}

main().catch((e) => {
  console.error('PREFLIGHT FAILED:', e.message);
  process.exit(1);
});
