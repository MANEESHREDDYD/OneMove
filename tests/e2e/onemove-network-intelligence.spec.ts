import { expect, test } from '@playwright/test';

/**
 * Records the OneMove network-intelligence walkthrough.
 *
 * The harness performs every call against the real API under a real session and
 * pushes the responses into the presentation route. It computes nothing: if the
 * backend does not return a field, the screen shows UNAVAILABLE rather than a
 * plausible substitute.
 *
 * Before a single narrative frame is allowed to run, a pre-flight gate asserts
 * the geography actually painted and that it is Bengaluru. Earlier recordings
 * were rejected for opening on a New York map, so this is checked rather than
 * assumed.
 */

const API = process.env.ONEMOVE_API_URL || 'http://127.0.0.1:8000';
const SHOTS = 'artifacts/swiggy-demo/final/screenshots';

/** Beat lengths in ms. They sum to roughly 4:10, the target runtime. */
const BEAT = {
  opening: 15_000,
  live: 24_000,
  observe: 24_000,
  mission: 30_000,
  bridge: 9_000,
  scenario: 20_000,
  impact: 22_000,
  optimizing: 24_000,
  result: 26_000,
  decision: 22_000,
  evidence: 21_000,
  replay: 23_000,
  closing: 13_000,
};

const EMAIL = process.env.TENANT_A_EMAIL;
const PASSWORD = process.env.TENANT_A_PASSWORD;
const WORKSPACE = process.env.DEMO_WORKSPACE_ID;

if (!EMAIL || !PASSWORD || !WORKSPACE) {
  throw new Error(
    'FAIL CLOSED: TENANT_A_EMAIL, TENANT_A_PASSWORD and DEMO_WORKSPACE_ID are required to record.',
  );
}

const WMO: Record<number, string> = {
  0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
  45: 'Fog', 48: 'Rime fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Dense drizzle',
  61: 'Slight rain', 63: 'Rain', 65: 'Heavy rain', 71: 'Snow', 80: 'Rain showers',
  81: 'Heavy showers', 82: 'Violent showers', 95: 'Thunderstorm',
};

const pct = (v: unknown) => (typeof v === 'number' ? `${(v / 100).toFixed(1)}%` : null);
const secs = (v: unknown) => (typeof v === 'number' ? `${v}s` : null);

test.describe('OneMove — network intelligence walkthrough', () => {
  test('records the full observe → stress → optimize → decide → prove → replay journey', async ({
    page,
    request,
  }) => {
    // ---- real session -------------------------------------------------
    const authRes = await request.post(
      `${process.env.NEXT_PUBLIC_SUPABASE_URL}/auth/v1/token?grant_type=password`,
      {
        headers: { apikey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '' },
        data: { email: EMAIL, password: PASSWORD },
      },
    );
    expect(authRes.ok(), 'tenant authentication must succeed').toBeTruthy();
    const token = (await authRes.json()).access_token;
    const headers = {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'x-workspace-id': WORKSPACE as string,
    };

    const push = (payload: Record<string, unknown>) =>
      page.evaluate((p) => (window as unknown as { __omDemo: (x: unknown) => void }).__omDemo(p), payload);

    // ---- pre-flight gate ----------------------------------------------
    // Nothing narrative happens until the geography is proven on screen.
    await page.goto('/demo/network-intelligence', { waitUntil: 'networkidle' });
    await page.waitForFunction(() => (window as unknown as { __omReady?: boolean }).__omReady === true, {
      timeout: 60_000,
    });
    await page.waitForSelector('[data-map-state="ready"]', { timeout: 60_000 });
    await page.waitForFunction(
      () => {
        const img = document.querySelector('img[data-layer="roads"]') as HTMLImageElement | null;
        return !!img && img.complete && img.naturalWidth > 0;
      },
      { timeout: 60_000 },
    );

    const zoneCount = Number(await page.getAttribute('[data-layer="overlay"]', 'data-zone-count'));
    expect(zoneCount, 'the full pilot network must be on screen').toBe(94);

    const body = (await page.textContent('body')) || '';
    for (const forbidden of ['New York', 'NEW YORK', 'Jersey City', 'JERSEY CITY', 'Times Square']) {
      expect(body, `pre-flight: "${forbidden}" must not appear`).not.toContain(forbidden);
    }

    // The basemap is generated from a bbox whose centre is asserted here, so a
    // regenerated asset pointing anywhere but Bengaluru fails before recording.
    const bbox = await page.evaluate(async () => {
      const r = await fetch('/demo/bengaluru-basemap.json');
      return (await r.json()).bbox as Record<string, number>;
    });
    const midLat = (bbox.min_lat + bbox.max_lat) / 2;
    const midLon = (bbox.min_lon + bbox.max_lon) / 2;
    expect(midLat, 'map must be centred on Bengaluru latitude').toBeGreaterThan(12.7);
    expect(midLat).toBeLessThan(13.2);
    expect(midLon, 'map must be centred on Bengaluru longitude').toBeGreaterThan(77.3);
    expect(midLon).toBeLessThan(77.9);

    // ---- external observations ----------------------------------------
    const wxRes = await request.get(
      'https://api.open-meteo.com/v1/forecast?latitude=12.9716&longitude=77.5946' +
        '&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m' +
        '&timezone=Asia%2FKolkata',
    );
    const wxCur = wxRes.ok() ? (await wxRes.json()).current : null;
    const weather = wxCur
      ? {
          condition: WMO[wxCur.weather_code] ?? `WMO ${wxCur.weather_code}`,
          temperature_c: wxCur.temperature_2m,
          precipitation_mm: wxCur.precipitation,
          humidity_pct: wxCur.relative_humidity_2m,
          wind_kmh: wxCur.wind_speed_10m,
          observed_at: new Date(`${wxCur.time}+05:30`).toISOString(),
        }
      : null;

    const trafficRes = await page.evaluate(async () => {
      const r = await fetch('/demo/bengaluru-traffic.json');
      return r.json();
    });
    const traffic = trafficRes as Record<string, unknown>;

    const matrix = await page.evaluate(async () => {
      const r = await fetch('/demo/bengaluru-basemap.json');
      return (await r.json()).zones.length as number;
    });
    expect(matrix).toBe(94);

    const api = async (path: string) => {
      const r = await request.get(`${API}${path}`, { headers });
      expect(r.ok(), `GET ${path}`).toBeTruthy();
      return r.json();
    };

    const zoneEvidence = (await api('/api/v1/evidence/zone/8860145b41fffff')).data;
    expect(zoneEvidence.evidence_class).toBe('PUBLIC_GEOGRAPHIC');

    // ---- 1. opening ----------------------------------------------------
    await push({ stage: 'opening' });
    await page.waitForTimeout(BEAT.opening);
    await page.screenshot({ path: `${SHOTS}/01-opening.png` });

    // ---- 2. live network ------------------------------------------------
    await push({
      stage: 'live',
      evidence: {
        source: zoneEvidence.source,
        source_version: zoneEvidence.source_version,
        evidence_class: zoneEvidence.evidence_class,
        h3_resolution: zoneEvidence.metadata?.h3_resolution,
      },
      candidates: [],
    });
    await page.waitForTimeout(BEAT.live);
    await page.screenshot({ path: `${SHOTS}/02-live-bengaluru.png` });

    // ---- 3. current weather + live traffic ------------------------------
    const candidates: string[] = await page.evaluate(async () => {
      const r = await fetch('/demo/facilities.json');
      return r.ok ? (await r.json()).facility_ids : [];
    });

    await push({ stage: 'observe', weather, traffic, candidates });
    await page.waitForTimeout(BEAT.observe);
    await page.screenshot({ path: `${SHOTS}/03-weather-traffic.png` });

    // ---- 3b. one simulated mission on the live network -------------------
    // The mission is synthetic. The route and both ETAs are real provider
    // values over Bengaluru's roads, which is what makes the delay meaningful.
    const mission = await page.evaluate(async () => {
      const r = await fetch('/demo/mission.json');
      return r.ok ? r.json() : null;
    });
    expect(mission, 'the mission route must be available').not.toBeNull();
    expect(mission.mission_class).toBe('SIMULATED');

    const MISSION_STATES = ['CREATED', 'ACCEPTED', 'PICKUP', 'EN ROUTE', 'DELIVERED'];
    const stateHold = Math.round(BEAT.mission * 0.12);
    const runHold = BEAT.mission - stateHold * 4;

    for (const st of ['CREATED', 'ACCEPTED', 'PICKUP']) {
      await push({ stage: 'mission', mission, missionState: st, missionProgress: 0, traffic, candidates });
      await page.waitForTimeout(stateHold);
    }

    // EN ROUTE: advance the courier along the real polyline.
    const steps = 40;
    for (let i = 0; i <= steps; i++) {
      await push({
        stage: 'mission',
        mission,
        missionState: 'EN ROUTE',
        missionProgress: i / steps,
        traffic,
        candidates,
      });
      await page.waitForTimeout(Math.round(runHold / steps));
    }
    await page.screenshot({ path: `${SHOTS}/03b-mission.png` });

    await push({ stage: 'mission', mission, missionState: 'DELIVERED', missionProgress: 1, traffic, candidates });
    await page.waitForTimeout(stateHold);

    await push({ stage: 'bridge', mission, traffic, candidates });
    await page.waitForTimeout(BEAT.bridge);
    await page.screenshot({ path: `${SHOTS}/03c-bridge.png` });

    // ---- 4. simulated counterfactual ------------------------------------
    const scRes = await request.post(`${API}/api/v1/scenarios`, {
      headers,
      data: {
        scenario_type: 'HEAVY_RAIN',
        description: 'Monsoon stress test over the Bengaluru pilot network (SIMULATED)',
        parameters: { travel_time_inflation_basis_points: 6000 },
        seed: 42,
      },
    });
    expect(scRes.ok(), 'scenario creation').toBeTruthy();
    const scenario = await scRes.json();
    const bp = scenario.parameters?.travel_time_inflation_basis_points;

    await push({
      stage: 'scenario',
      weather,
      traffic,
      candidates,
      scenario: {
        scenario_id: scenario.scenario_id,
        scenario_type: scenario.scenario_type,
        shock: typeof bp === 'number' ? `+${(bp / 100).toFixed(0)}% travel time` : null,
      },
    });
    await page.waitForTimeout(BEAT.scenario);
    await page.screenshot({ path: `${SHOTS}/04-scenario.png` });

    // ---- 5. derived impact ----------------------------------------------
    const impactDoc = await api(`/api/v1/scenarios/${scenario.scenario_id}`);
    await push({
      stage: 'impact',
      impact: {
        coverage: pct(impactDoc.coverage_basis_points),
        p50: secs(impactDoc.p50_duration_seconds),
        p90: secs(impactDoc.p90_duration_seconds),
        p95: secs(impactDoc.p95_duration_seconds),
        disconnected:
          typeof impactDoc.disconnected_zones_count === 'number'
            ? String(impactDoc.disconnected_zones_count)
            : null,
        redundancy: pct(impactDoc.redundancy_index_basis_points),
        grade: impactDoc.degradation_grade ?? null,
      },
    });
    await page.waitForTimeout(BEAT.impact);
    await page.screenshot({ path: `${SHOTS}/05-impact.png` });

    // ---- 6. real CP-SAT, asynchronous ------------------------------------
    const jobRes = await request.post(`${API}/api/v1/optimizations`, {
      headers,
      data: {
        idempotency_key: `demo-${Date.now()}`,
        min_open_facilities: 1,
        max_open_facilities: 4,
        max_travel_seconds: 1800,
        allow_uncovered_demand: true,
        scenarios: ['s1_free_flow', 's2_congested', 's3_congested_outage'],
      },
    });
    expect(jobRes.ok(), 'optimization submission').toBeTruthy();
    const jobId = (await jobRes.json()).job_id;

    await push({ stage: 'optimizing', job: { job_id: jobId, status: 'QUEUED' } });
    await page.waitForTimeout(Math.round(BEAT.optimizing * 0.3));

    // Poll the real job. The worker is a separate process, exactly as deployed.
    let job: Record<string, unknown> | null = null;
    const deadline = Date.now() + 180_000;
    let sawRunning = false;
    while (Date.now() < deadline) {
      const cur = await api(`/api/v1/optimizations/${jobId}`);
      if (!sawRunning && (cur.status === 'RUNNING' || cur.status === 'CLAIMED')) {
        sawRunning = true;
        await push({ stage: 'optimizing', job: { job_id: jobId, status: 'RUNNING' } });
      }
      if (cur.status === 'SUCCESS' || cur.solver_status) {
        job = cur;
        break;
      }
      await page.waitForTimeout(1500);
    }
    expect(job, 'CP-SAT must complete within the recording window').not.toBeNull();
    const rd = job!.result_document as Record<string, any>;
    expect(rd.status, 'solver status').toBe('OPTIMAL');

    await push({ stage: 'optimizing', job: { job_id: jobId, status: 'OPTIMAL' } });
    await page.waitForTimeout(Math.round(BEAT.optimizing * 0.35));
    await page.screenshot({ path: `${SHOTS}/06-optimization.png` });

    // ---- 7. result, selected facilities on the map -----------------------
    const selected = job!.opened_facilities as string[];
    const scenarioCount = new Set(rd.assignments.map((a: Record<string, string>) => a.scenario_id)).size;

    await push({
      stage: 'result',
      candidates,
      selected,
      result: {
        status: rd.status,
        job_id: jobId,
        action: rd.action,
        opened_count: String(selected.length),
        scenario_count: String(scenarioCount),
        objective: Number(rd.objective.weighted_total).toLocaleString('en-US'),
        runtime: job!.run_duration_ms ? `${job!.run_duration_ms} ms` : null,
        solver_version: rd.solver_version,
        assumption_version: String(rd.objective.weights.assumption_version).split('+')[0],
      },
    });
    await page.waitForTimeout(BEAT.result);
    await page.screenshot({ path: `${SHOTS}/07-selected-facilities.png` });

    // ---- 8. authoritative decision freeze --------------------------------
    const frRes = await request.post(`${API}/api/v1/decisions/freeze`, {
      headers,
      data: {
        optimization_job_id: jobId,
        operator_rationale: 'Monsoon stress test — capacity configuration accepted',
      },
    });
    expect(frRes.ok(), 'decision freeze').toBeTruthy();
    const decision = await frRes.json();

    await push({
      stage: 'decision',
      candidates,
      selected,
      decision: {
        // The frozen record names its action `selected_action`, not
        // `decision_type`; the latter rendered UNAVAILABLE next to an otherwise
        // complete ledger entry. `feature_snapshot_hash` is what ties the
        // decision to the exact inputs, so it belongs on screen too.
        decision_id: decision.decision_id,
        selected_action: decision.selected_action,
        decision_time: decision.decision_time,
        facilities: `${(decision.opened_facilities ?? selected).length} opened`,
        dataset_version: decision.dataset_version ?? rd.dataset_version,
        network_version: decision.network_version ?? rd.network_version,
        solver_version: decision.solver_version ?? rd.solver_version,
        feature_snapshot_hash: decision.feature_snapshot_hash?.slice(0, 24),
        code_sha: decision.code_sha,
      },
    });
    await page.waitForTimeout(BEAT.decision);
    await page.screenshot({ path: `${SHOTS}/08-decision.png` });

    // ---- 9. evidence lineage ---------------------------------------------
    await push({
      stage: 'evidence',
      candidates,
      selected,
      lineage: [
        { label: 'Decision', id: decision.decision_id, cls: 'DERIVED' },
        { label: 'Optimization result', id: jobId, cls: 'DERIVED' },
        { label: 'Problem snapshot', id: rd.problem_snapshot_id, cls: 'DERIVED' },
        { label: 'Travel matrix', id: rd.problem_fingerprint?.slice(0, 32), cls: 'PUBLIC_GEOGRAPHIC' },
        { label: 'Network graph', id: rd.network_version, cls: 'PUBLIC_GEOGRAPHIC' },
        { label: 'Scenario', id: scenario.scenario_id, cls: 'SIMULATED' },
        {
          label: 'Assumption set',
          id: String(rd.objective.weights.assumption_version).split('+')[0],
          cls: 'ASSUMPTION',
        },
        { label: 'Release', id: decision.code_sha?.slice(0, 32), cls: 'DERIVED' },
      ],
    });
    await page.waitForTimeout(BEAT.evidence);
    await page.screenshot({ path: `${SHOTS}/09-evidence.png` });

    // ---- 10. point-in-time replay -----------------------------------------
    const rpRes = await request.post(`${API}/api/v1/decisions/${decision.decision_id}/replay`, {
      headers,
      data: {},
    });
    expect(rpRes.ok(), 'replay').toBeTruthy();
    const replay = await rpRes.json();
    // Displayed as returned. Asserting EXACT_MATCH here would hide a real DRIFT.
    expect(['EXACT_MATCH', 'SEMANTIC_MATCH', 'DRIFT', 'NON_REPLAYABLE']).toContain(replay.match_status);

    const yesNo = (v: unknown) => (v === true ? 'YES' : v === false ? 'NO' : null);
    await push({
      stage: 'replay',
      candidates,
      selected,
      replay: {
        // These are the names the replay endpoint really returns. An earlier
        // pass guessed frozen_action_hash / recomputed_action_hash and both
        // hashes rendered UNAVAILABLE beside a green EXACT_MATCH, which is the
        // one place in the video where a viewer most wants to see the numbers.
        decision_id: replay.original_decision_id ?? decision.decision_id,
        decision_time: decision.decision_time,
        as_of: replay.replayed_at ?? decision.decision_time,
        assumption: String(rd.objective.weights.assumption_version).split('+')[0],
        pit_valid: yesNo(replay.pit_valid),
        frozen_hash: replay.expected_hash ?? null,
        recomputed_hash: replay.actual_hash ?? null,
        action_reproduced: yesNo(replay.reproduced_exact_action),
        facilities_reproduced: yesNo(replay.reproduced_exact_facilities),
        objective_match: yesNo(replay.objective_match),
        match_status: replay.match_status,
      },
    });
    await page.waitForTimeout(BEAT.replay);
    await page.screenshot({ path: `${SHOTS}/10-replay.png` });

    // ---- 11. closing --------------------------------------------------------
    await push({ stage: 'closing', candidates, selected });
    await page.waitForTimeout(BEAT.closing);
    await page.screenshot({ path: `${SHOTS}/11-closing.png` });

    // A last assertion on what the viewer actually ended up looking at. This
    // reads rendered text, not document.body.textContent -- the latter includes
    // Next's serialised RSC payload, whose own encoding contains the literal
    // word "undefined" and fails the check on a perfectly clean screen.
    const visible = await page.evaluate(() => (document.body as HTMLElement).innerText);
    for (const bad of ['New York', 'Jersey City', 'undefined', '${', 'NaN']) {
      expect(visible, `closing frame must not show "${bad}"`).not.toContain(bad);
    }
  });
});
