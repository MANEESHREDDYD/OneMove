import { execFile, execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { promisify } from 'node:util';

import { expect, test } from '@playwright/test';
import dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

const run = promisify(execFile);
const API = process.env.ONEMOVE_API_URL || 'http://127.0.0.1:8000';
const OPERATE = '/demo/operate';
const RECORD = process.env.ONEMOVE_DEMO_RECORD === '1';
const VERSION = process.env.ONEMOVE_DEMO_VERSION;
const PRECHECK = process.env.ONEMOVE_DEMO_PRECHECK === '1';

const sceneHold = (scene: string) => {
  if (!RECORD) return 200;
  if (!VERSION) throw new Error('ONEMOVE_DEMO_VERSION is required while recording.');
  const audioPath = path.join(process.cwd(), 'artifacts', 'demo', 'audio', VERSION, `${scene}.mp3`);
  const ffprobe = process.env.ONEMOVE_FFPROBE || 'ffprobe';
  const seconds = Number(execFileSync(ffprobe, [
    '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audioPath,
  ], { encoding: 'utf8' }).trim());
  if (!Number.isFinite(seconds) || seconds <= 0) throw new Error(`No valid narration duration for ${scene}.`);
  return Math.ceil(seconds * 1000) + 700;
};

const HOLD = Object.fromEntries([
  'opening', 'network', 'live', 'mission', 'disruption', 'comparison', 'why',
  'architecture', 'freeze', 'evidence', 'replay', 'closing',
].map((scene) => [scene, sceneHold(scene)])) as Record<string, number>;

const required = (name: string) => {
  const value = process.env[name];
  if (!value) throw new Error(`FAIL CLOSED: ${name} is required for the demo journey.`);
  return value;
};

test('records the OPERATE → recommend → evidence → replay golden path', async ({ page, request }) => {
  test.setTimeout(RECORD ? 900_000 : 420_000);

  const screenshotDir = path.join(process.cwd(), 'artifacts', 'demo', 'precheck');
  if (PRECHECK) mkdirSync(screenshotDir, { recursive: true });
  const shot = async (name: string) => {
    if (PRECHECK) await page.screenshot({ path: path.join(screenshotDir, `${name}.png`), fullPage: false });
  };

  const authResponse = await request.post(
    `${required('NEXT_PUBLIC_SUPABASE_URL')}/auth/v1/token?grant_type=password`,
    {
      headers: { apikey: required('NEXT_PUBLIC_SUPABASE_ANON_KEY') },
      data: { email: required('TENANT_A_EMAIL'), password: required('TENANT_A_PASSWORD') },
    },
  );
  expect(authResponse.ok(), 'demo authentication').toBeTruthy();
  const token = (await authResponse.json()).access_token as string;
  const workspace = required('DEMO_WORKSPACE_ID');
  const headers = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
    'x-workspace-id': workspace,
  };

  const apiGet = async (path: string) => {
    const response = await request.get(`${API}${path}`, { headers });
    expect(response.ok(), `GET ${path}: ${await response.text()}`).toBeTruthy();
    return response.json();
  };

  const liveContext = await apiGet('/api/v1/demo/live-context');

  const push = async (payload: Record<string, unknown>) => {
    await page.evaluate((next) => {
      const driver = (window as unknown as { __omOperateDemo?: (value: unknown) => void }).__omOperateDemo;
      if (!driver) throw new Error('OPERATE demo driver is unavailable');
      driver(next);
    }, payload);
  };

  await page.setExtraHTTPHeaders({ Authorization: `Bearer ${token}`, 'x-workspace-id': workspace });
  await page.goto(OPERATE, { waitUntil: 'networkidle' });
  await page.waitForFunction(
    () => (window as unknown as { __omOperateReady?: boolean }).__omOperateReady === true,
  );
  await expect(page.locator('[data-map-state="ready"]')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('canvas.maplibregl-canvas')).toBeVisible({ timeout: 30_000 });

  const rendered = await page.evaluate(() => {
    const map = (window as unknown as {
      __omMap?: { queryRenderedFeatures: (options: { layers: string[] }) => unknown[] };
    }).__omMap;
    return {
      roads: map?.queryRenderedFeatures({ layers: ['roads-line'] }).length ?? 0,
      routes: map?.queryRenderedFeatures({ layers: ['routes-line'] }).length ?? 0,
    };
  });
  expect(rendered.roads, 'rendered road features').toBeGreaterThan(0);
  expect(rendered.routes, 'rendered route features').toBeGreaterThan(0);
  await expect(page.getByTestId('map-geographic-context')).toContainText('BENGALURU · KARNATAKA, INDIA');
  await expect(page.getByTestId('map-geographic-context')).toContainText('Jayanagar · Koramangala · Indiranagar · HSR');
  await expect(page.getByTestId('map-locator')).toContainText('PILOT');
  await expect(page.locator('[data-label-kind="locality"]')).toHaveCount(7);
  await expect(page.locator('[data-label-kind="road"]', { hasText: 'Outer Ring Road' }).first()).toBeAttached();
  await expect(page.locator('[data-label-kind="road"]', { hasText: 'Hosur Road' }).first()).toBeAttached();
  await expect(page.getByTestId('map-operational-legend')).toContainText('Recommended');

  const geographicLayers = await page.evaluate(() => {
    const map = (window as unknown as {
      __omMap?: { queryRenderedFeatures: (options: { layers: string[] }) => unknown[] };
    }).__omMap;
    return {
      pilot: map?.queryRenderedFeatures({ layers: ['pilot-area-outline'] }).length ?? 0,
      h3: map?.queryRenderedFeatures({ layers: ['zones-outline'] }).length ?? 0,
    };
  });
  expect(geographicLayers.pilot, 'rendered pilot boundary').toBeGreaterThan(0);
  expect(geographicLayers.h3, 'rendered H3 context').toBeGreaterThan(0);

  const basemapResponse = await request.get('http://localhost:3000/demo/bengaluru-basemap.json');
  const basemap = await basemapResponse.json();
  expect(basemap.evidence_class).toBe('PUBLIC_GEOGRAPHIC');
  expect(basemap.zones).toHaveLength(94);
  expect(basemap.roads.length).toBeGreaterThan(10_000);

  const missionResponse = await request.get('http://localhost:3000/demo/mission-routes.json');
  const mission = await missionResponse.json();
  expect(mission.evidence_class).toBe('SIMULATED');
  expect(mission.orders).toHaveLength(16);
  expect(mission.routes).toHaveLength(16);
  expect(mission.traffic_aware).toBe(false);
  expect(mission.routes.every((route: { geometry: unknown[] }) => route.geometry.length > 2)).toBeTruthy();

  await expect(page.getByTestId('live-context-panel')).toContainText('PROVIDER_ESTIMATED');
  await expect(page.getByTestId('live-context-panel')).toContainText('PUBLIC_OFFICIAL');
  const trafficFreshness = await page.locator('[data-source="Traffic"]').getAttribute('data-freshness');
  expect(['FRESH', 'DEGRADED', 'STALE', 'UNAVAILABLE']).toContain(trafficFreshness);

  await push({ stage: 'opening' });
  await shot('01-opening');
  await page.waitForTimeout(HOLD.opening);
  await push({ stage: 'network' });
  await shot('02-network');
  await page.waitForTimeout(HOLD.network);
  await page.waitForTimeout(HOLD.live);

  await push({ stage: 'mission' });
  await page.locator('[data-order-id="ORD-009"]').click();
  await expect(page.getByTestId('order-detail')).toContainText('ORD-009');
  await expect(page.getByTestId('order-detail')).toContainText('not traffic-aware');
  await shot('03-mission');
  await page.waitForTimeout(HOLD.mission);

  const facilitiesResponse = await request.get('http://localhost:3000/demo/facilities.json');
  const facilityIds = (await facilitiesResponse.json()).facility_ids as string[];
  const baseline = {
    baseline_id: 'simulated-demo-baseline-cto-outreach-v1',
    facility_ids: facilityIds.slice(0, 4),
    source: 'cto-outreach-v1 controlled demo scenario definition; not a retailer network',
    evidence_class: 'SIMULATED',
    as_of: null,
  };

  await push({ stage: 'disruption' });
  await expect(page.getByTestId('simulated-disruption')).toContainText('SIMULATED SCENARIO');
  await shot('04-disruption');
  await page.waitForTimeout(HOLD.disruption);

  const sha = (await run('git', ['rev-parse', 'HEAD'], { cwd: process.cwd() })).stdout.trim();
  const submit = await request.post(`${API}/api/v1/optimizations`, {
    headers,
    data: {
      idempotency_key: `cto-outreach-v1-${sha.slice(0, 16)}`,
      min_open_facilities: 1,
      max_open_facilities: 4,
      max_travel_seconds: 1800,
      allow_uncovered_demand: true,
      scenarios: ['s1_free_flow', 's2_congested', 's3_congested_outage'],
      do_nothing_baseline: baseline,
    },
  });
  expect(submit.ok(), `optimization submission: ${await submit.text()}`).toBeTruthy();
  const submitted = await submit.json();
  const jobId = submitted.job_id as string;

  if (!['SUCCESS', 'FAILED'].includes(submitted.status)) {
    try {
      const workerEnv = {
        ...process.env,
        DATABASE_URL: required('DATABASE_URL'),
        TEST_DATABASE_URL: process.env.TEST_DATABASE_URL || required('DATABASE_URL'),
        ZONEPILOT_DATA_ROOT: process.env.ZONEPILOT_DATA_ROOT || require('path').join(process.cwd(), 'data_root'),
        PYTHONPATH: process.cwd(),
      };
      await run('python', ['scripts/demo/local_worker.py', '--job-id', jobId], {
        cwd: process.cwd(),
        env: workerEnv,
        timeout: 300_000,
        maxBuffer: 2 * 1024 * 1024,
      });
    } catch {
      // A deployed worker may win the lease. The authoritative status below is
      // the only outcome that decides whether the journey continues.
    }
  }

  let optimization: Record<string, unknown> | null = null;
  const solveDeadline = Date.now() + 330_000;
  while (Date.now() < solveDeadline) {
    const current = await apiGet(`/api/v1/optimizations/${jobId}`);
    if (current.status === 'SUCCESS' || current.status === 'FAILED') {
      optimization = current;
      break;
    }
    // The optimization endpoint has an intentionally small identity budget.
    // CP-SAT may run for two minutes, so polling faster than this only rate
    // limits the presenter without making the result arrive sooner.
    await page.waitForTimeout(10_000);
  }
  expect(optimization, 'optimization completed').not.toBeNull();
  expect(optimization!.solver_status).toBe('OPTIMAL');
  const result = optimization!.result_document as Record<string, unknown>;
  const comparison = result.baseline_comparison as Record<string, unknown>;
  expect(comparison.status).toBe('AVAILABLE');
  expect(comparison.baseline_facility_ids as string[]).toEqual(baseline.facility_ids);

  const optimizationScene = {
    job_id: jobId,
    opened_facilities: optimization!.opened_facilities,
    run_duration_ms: optimization!.run_duration_ms,
    result_document: result,
  };
  await push({ stage: 'comparison', optimization: optimizationScene });
  await expect(page.getByTestId('do-nothing')).toContainText('SIMULATED DEMO BASELINE');
  await expect(page.getByTestId('recommended')).toContainText('RECOMMENDED');
  await expect(page.getByTestId('comparison-delta')).toBeVisible();
  await expect(page.locator('[data-decision-kind="recommended"]')).toHaveCount(4);
  await page.waitForFunction(() => {
    const map = (window as unknown as {
      __omMap?: { queryRenderedFeatures: (options: { layers: string[] }) => unknown[] };
    }).__omMap;
    return (map?.queryRenderedFeatures({ layers: ['baseline-point'] }).length ?? 0) > 0
      && (map?.queryRenderedFeatures({ layers: ['recommended-point'] }).length ?? 0) > 0;
  });
  const decisionGeography = await page.evaluate(() => {
    const map = (window as unknown as {
      __omMap?: { queryRenderedFeatures: (options: { layers: string[] }) => unknown[] };
    }).__omMap;
    return {
      baseline: map?.queryRenderedFeatures({ layers: ['baseline-point'] }).length ?? 0,
      recommended: map?.queryRenderedFeatures({ layers: ['recommended-point'] }).length ?? 0,
    };
  });
  expect(decisionGeography.baseline, 'Do Nothing facilities on map').toBeGreaterThan(0);
  expect(decisionGeography.recommended, 'recommended facilities on map').toBeGreaterThan(0);
  await shot('05-comparison');
  await page.waitForTimeout(HOLD.comparison);

  await push({ stage: 'why', optimization: optimizationScene });
  await expect(page.getByTestId('why-decision')).toContainText('WHY THIS DECISION?');
  await expect(page.getByTestId('why-decision')).toContainText('Objective components');
  await shot('06-why');
  await page.waitForTimeout(HOLD.why);

  await push({ stage: 'architecture', optimization: optimizationScene });
  await expect(page.getByTestId('architecture-story')).toContainText('OR-Tools CP-SAT');
  await expect(page.getByTestId('architecture-story')).toContainText('PostgreSQL Decision Ledger');
  await expect(page.getByTestId('architecture-story')).toContainText('Point-in-Time Replay');
  await shot('07-architecture');
  await page.waitForTimeout(HOLD.architecture);

  const freezeResponse = await request.post(`${API}/api/v1/decisions/freeze`, {
    headers,
    data: {
      optimization_job_id: jobId,
      operator_rationale: 'Controlled Bengaluru disruption demo recommendation accepted for reproducibility.',
    },
  });
  expect(freezeResponse.ok(), `decision freeze: ${await freezeResponse.text()}`).toBeTruthy();
  const decision = await freezeResponse.json();
  await push({ stage: 'freeze', optimization: optimizationScene, decision });
  await expect(page.getByTestId('frozen-decision')).toContainText(decision.decision_id);
  await shot('08-freeze');
  await page.waitForTimeout(HOLD.freeze);

  const scenarioInputs = result.scenario_inputs as {
    scenario_id: string;
    matrix_id: string;
    evidence_class: string;
  }[];
  const evidence = [
    { label: 'Decision', id: decision.decision_id, evidence_class: 'DERIVED' },
    { label: 'Optimization result', id: jobId, evidence_class: 'DERIVED' },
    { label: 'Problem snapshot', id: result.problem_snapshot_id, evidence_class: 'DERIVED' },
    ...scenarioInputs.map((item) => ({
      label: item.scenario_id,
      id: item.matrix_id,
      evidence_class: item.evidence_class === 'PUBLIC_GEOGRAPHIC' ? 'PUBLIC_GEOGRAPHIC' : 'SIMULATED',
    })),
    { label: 'Demo baseline', id: baseline.baseline_id, evidence_class: 'SIMULATED' },
    { label: 'Assumption set', id: result.assumption_version, evidence_class: 'ASSUMPTION' },
    { label: 'Traffic context', id: `${liveContext.capture_run_id}:traffic`, evidence_class: 'PROVIDER_ESTIMATED' },
    { label: 'Weather context', id: `${liveContext.capture_run_id}:weather`, evidence_class: 'PUBLIC_OFFICIAL' },
    { label: 'Release', id: decision.code_sha, evidence_class: 'DERIVED' },
  ];
  await push({ stage: 'evidence', optimization: optimizationScene, decision, evidence });
  await expect(page.getByTestId('decision-evidence')).toContainText('Decision evidence');
  await expect(page.getByTestId('decision-evidence')).toContainText('SIMULATED');
  await expect(page.getByTestId('decision-evidence')).toContainText('PROVIDER_ESTIMATED');
  await expect(page.getByTestId('decision-evidence')).toContainText('PUBLIC_OFFICIAL');
  await shot('09-evidence');
  await page.waitForTimeout(HOLD.evidence);

  const replayResponse = await request.post(
    `${API}/api/v1/decisions/${decision.decision_id}/replay`,
    { headers, data: {} },
  );
  expect(replayResponse.ok(), `decision replay: ${await replayResponse.text()}`).toBeTruthy();
  const replay = await replayResponse.json();
  expect(['EXACT_MATCH', 'SEMANTIC_MATCH']).toContain(replay.match_status);
  expect(replay.pit_valid).toBe(true);
  expect(replay.reproduced_exact_action).toBe(true);
  expect(replay.reproduced_exact_facilities).toBe(true);
  await push({ stage: 'replay', optimization: optimizationScene, decision, evidence, replay });
  await expect(page.getByTestId('decision-replay')).toContainText(replay.match_status);
  await expect(page.getByTestId('decision-replay')).not.toContainText('No replay result');
  await shot('10-replay');
  await page.waitForTimeout(HOLD.replay);

  const html = await page.content();
  expect(html).not.toMatch(/api\.tomtom\.com/i);
  expect(html).not.toMatch(/[?&]key=/i);
  expect(html).not.toMatch(/service_role/i);
  expect(html).not.toContain(token);

  await push({ stage: 'closing', optimization: optimizationScene, decision, evidence, replay });
  await expect(page.getByTestId('demo-closing')).toContainText('Operate.');
  await expect(page.getByTestId('demo-closing')).toContainText("OneMove doesn't just recommend an action.");
  await expect(page.getByTestId('demo-closing')).toContainText('The goal is not another dashboard.');
  await shot('11-closing');
  await page.waitForTimeout(HOLD.closing);
});
