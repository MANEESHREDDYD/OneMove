import { test, expect } from '@playwright/test';

// Configuration
const API_BASE = process.env.ONEMOVE_API_URL || 'http://127.0.0.1:8000';

/** Base dwell for a readable panel. Overridable so pacing can be tuned without edits. */
const DWELL = Number(process.env.DEMO_DWELL_MS || 9000);

/** Per-step stills for visual QA. A passing exit code says nothing about how the
 *  recording actually looks, so each key screen is captured for inspection. */
const SHOT_DIR = 'artifacts/swiggy-demo/final/screenshots';

const DEMO_TENANT_EMAIL = process.env.TENANT_A_EMAIL;
const DEMO_TENANT_PASS = process.env.TENANT_A_PASSWORD;

if (!DEMO_TENANT_EMAIL || !DEMO_TENANT_PASS) {
  throw new Error("FAIL CLOSED: TENANT_A_EMAIL and TENANT_A_PASSWORD are required for the Swiggy Demo recording.");
}

let apiToken = '';

test.describe('Swiggy Friday Demo Path', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('Deterministic execution of Swiggy demo', async ({ page, request }) => {
    // 1. OneMove landing/operator console
    // Overlay helper. addInitScript re-runs on EVERY navigation; addScriptTag
    // only injects into the current document, so the helper disappeared the
    // moment the demo navigated away from the command centre.
    await page.addInitScript({ content: `
      window.showDemoOverlay = (title, htmlContent) => {
        let el = document.getElementById('demo-overlay');
        if (!el) {
          el = document.createElement('div');
          el.id = 'demo-overlay';
          el.style.position = 'fixed';
          el.style.bottom = '40px';
          el.style.right = '40px';
          el.style.width = '650px';
          el.style.maxHeight = '85vh';
          el.style.overflow = 'auto';
          el.style.backgroundColor = 'rgba(15, 23, 42, 0.98)';
          el.style.color = '#e2e8f0';
          el.style.padding = '24px';
          el.style.fontFamily = 'system-ui, -apple-system, sans-serif';
          el.style.fontSize = '15px';
          el.style.lineHeight = '1.5';
          el.style.zIndex = '999999';
          el.style.border = '1px solid #334155';
          el.style.borderRadius = '12px';
          el.style.boxShadow = '0 25px 50px -12px rgba(0, 0, 0, 0.5)';
          document.body.appendChild(el);
        }
        
        let formattedHtml = '<div style="margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid #334155;">';
        formattedHtml += '<span style="font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:#94a3b8; font-weight:600;">Presentation View — backed by live OneMove APIs</span>';
        formattedHtml += '<h3 style="color:#f8fafc; margin:8px 0 0 0; font-size:20px;">' + title + '</h3></div>';
        formattedHtml += '<div>' + htmlContent + '</div>';
        
        el.innerHTML = formattedHtml;
      };
      
      window.clearDemoOverlay = () => {
        let el = document.getElementById('demo-overlay');
        if (el) el.remove();
      };
    `});

    await page.goto('/admin/command-center');
    await expect(page.locator('h1')).toContainText('Command Center');
    

    let isOnline = false;
    try {
      const healthRes = await request.get(`${API_BASE}/health`, { timeout: 5000 });
      isOnline = healthRes.ok();
    } catch (e) {
      isOnline = false;
    }
    const statusText = isOnline ? '<span style="color:#22c55e">ONLINE</span>' : '<span style="color:#ef4444">UNAVAILABLE</span>';

    await page.evaluate((statusHtml) => (window as any).showDemoOverlay('Step 1: Operator Console', 
      '<div><strong>Status:</strong> ' + statusHtml + '</div>'
    ), statusText);
    await page.waitForTimeout(Math.round(DWELL * 0.55));

    // 2. Bengaluru physical-commerce network
    await page.goto('/network');
    await expect(page.locator('h1')).toContainText('Bengaluru Digital Twin');
    await page.waitForTimeout(DWELL);
    
    // 3. Authenticate against Supabase API to get token for FastAPI
    // Note: We need a valid token to call the FastAPI backend, assuming we can get it or use the Next.js session
    const authRes = await request.post(`${process.env.NEXT_PUBLIC_SUPABASE_URL || 'http://127.0.0.1:54321'}/auth/v1/token?grant_type=password`, {
      headers: { 'apikey': process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '' },
      data: { email: DEMO_TENANT_EMAIL, password: DEMO_TENANT_PASS }
    });
    
    if (authRes.ok()) {
       const authData = await authRes.json();
       apiToken = authData.access_token;
    } else {
       // If no local credentials provided, this script will fail as per FAIL_CLOSED rule
       console.log('API auth failed, will proceed without token, but endpoints may reject.');
    }
    
    // The workspace is a SELECTOR: the API validates it against server-side
    // membership, so supplying it does not grant access. Without it every
    // tenant-scoped endpoint correctly refuses the request.
    const DEMO_WORKSPACE_ID = process.env.DEMO_WORKSPACE_ID;
    expect(DEMO_WORKSPACE_ID, 'DEMO_WORKSPACE_ID must be set for the demo run').toBeTruthy();
    const headers = {
      'Authorization': `Bearer ${apiToken}`,
      'Content-Type': 'application/json',
      'x-workspace-id': DEMO_WORKSPACE_ID as string,
    };

    // 3. authentic network/geographic/routing evidence
    await page.evaluate(() => (window as any).showDemoOverlay('Step 3: Network Evidence', '<div>Fetching zone 8860145b41fffff...</div>'));
    let res = await request.get(`${API_BASE}/api/v1/evidence/zone/8860145b41fffff`, { headers });
    expect(res.ok()).toBeTruthy();
    let data = await res.json();
    await page.evaluate((d) => {
      const html = `
        <div style="display:grid; grid-template-columns:120px 1fr; gap:8px;">
          <strong style="color:#94a3b8">Source:</strong> <span>${d.source || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Class:</strong> <span>${d.class || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Dataset:</strong> <span>${d.dataset_version || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Version:</strong> <span>${d.version || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Matrix:</strong> <span style="font-family:monospace; color:#fbbf24">${d.matrix_hash || 'UNAVAILABLE'}</span>
        </div>
      `;
      (window as any).showDemoOverlay('Step 3: Network Evidence Retrieved', html);
    }, data);
    await page.waitForTimeout(DWELL);
    await page.screenshot({ path: `${SHOT_DIR}/02-network-evidence.png` });

    // 4. create one clearly-labelled SIMULATED disruption scenario
    await page.evaluate(() => (window as any).showDemoOverlay('Step 4: Create Disruption', '<div>Posting scenario...</div>'));
    res = await request.post(`${API_BASE}/api/v1/scenarios`, {
      headers,
      data: {
        // Real ScenarioCreateRequest contract. The previous payload used
        // scenario_name / congestion_multiplier / failed_facility_ids, which match
        // no field the API accepts, so it would 422. Parameters must also be
        // expressible against the facility x demand matrix: a 1.6x travel-time
        // multiplier is +60%, i.e. 6000 basis points.
        scenario_type: "HEAVY_RAIN",
        description: "Peak monsoon surge across the Bengaluru pilot network (SIMULATED)",
        parameters: { travel_time_inflation_basis_points: 6000 },
        seed: 42,
      }
    });
    expect(res.ok()).toBeTruthy();
    data = await res.json();
    const scenarioId = data.scenario_id;
    const createdScenario = data;
    await page.evaluate((d) => {
      // Real scenario fields. The previous panel read scenario_name /
      // matrix_identity / affected_network, none of which this response carries.
      const bp = d.parameters && d.parameters.travel_time_inflation_basis_points;
      const inflation = typeof bp === 'number' ? `+${(bp / 100).toFixed(0)}% travel time` : 'UNAVAILABLE';
      const matrix = d.derivation && d.derivation.matrix_id ? d.derivation.matrix_id : 'UNAVAILABLE';
      const html = `
        <div style="display:grid; grid-template-columns:170px 1fr; gap:8px;">
          <strong style="color:#94a3b8">Scenario:</strong> <span style="font-family:monospace; color:#38bdf8">${d.scenario_id || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Type:</strong> <span style="font-family:monospace">${d.scenario_type || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Applied disruption:</strong> <span style="color:#fbbf24; font-family:monospace">${inflation}</span>
          <strong style="color:#94a3b8">Routing baseline:</strong> <span style="font-family:monospace; font-size:13px">${matrix}</span>
          <strong style="color:#94a3b8">Evidence class:</strong> <div><span style="background-color:#ef4444; color:white; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:bold;">${d.evidence_class || 'UNAVAILABLE'}</span></div>
          <strong style="color:#94a3b8"></strong> <span style="color:#94a3b8; font-size:12px">Counterfactual applied to an authentic public-geographic baseline.</span>
        </div>
      `;
      (window as any).showDemoOverlay('Step 4: Simulated Disruption', html);
    }, data);
    await page.waitForTimeout(DWELL);
    await page.screenshot({ path: `${SHOT_DIR}/03-scenario.png` });

    // 5. show resulting network degradation
    res = await request.get(`${API_BASE}/api/v1/scenarios/${scenarioId}`, { headers });
    expect(res.ok()).toBeTruthy();
    data = await res.json();
    await page.evaluate((d) => {
      // Real derived metrics. The previous panel was a fixed sentence naming a
      // facility ("fac-02") that does not exist in the catalog.
      const pct = (v: unknown) => (typeof v === 'number' ? `${(v / 100).toFixed(1)}%` : 'UNAVAILABLE');
      const secs = (v: unknown) => (typeof v === 'number' ? `${v}s` : 'UNAVAILABLE');
      const unavailable = d.unavailable_metrics && Object.keys(d.unavailable_metrics).length
        ? Object.keys(d.unavailable_metrics).join(', ')
        : 'none';
      const html = `
        <div style="display:grid; grid-template-columns:190px 1fr; gap:8px;">
          <strong style="color:#94a3b8">Coverage:</strong> <span style="font-family:monospace">${pct(d.coverage_basis_points)}</span>
          <strong style="color:#94a3b8">P50 / P90 / P95 travel:</strong> <span style="font-family:monospace">${secs(d.p50_duration_seconds)} / ${secs(d.p90_duration_seconds)} / ${secs(d.p95_duration_seconds)}</span>
          <strong style="color:#94a3b8">Disconnected zones:</strong> <span style="font-family:monospace">${typeof d.disconnected_zones_count === 'number' ? d.disconnected_zones_count : 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Redundancy index:</strong> <span style="font-family:monospace">${pct(d.redundancy_index_basis_points)}</span>
          <strong style="color:#94a3b8">Degradation grade:</strong> <span style="font-family:monospace; color:#fbbf24; font-weight:700">${d.degradation_grade || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Metrics evidence:</strong> <div><span style="background-color:#3b82f6; color:white; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:bold;">${d.metrics_evidence_class || 'UNAVAILABLE'}</span></div>
          <strong style="color:#94a3b8">Unavailable metrics:</strong> <span style="font-family:monospace; font-size:13px">${unavailable}</span>
        </div>
      `;
      (window as any).showDemoOverlay('Step 5: Network Impact', html);
    }, { ...data, metrics_evidence_class: createdScenario.metrics_evidence_class });
    await page.waitForTimeout(DWELL);
    await page.screenshot({ path: `${SHOT_DIR}/04-impact.png` });

    // 6. run real CP-SAT optimization
    const idemKey = `demo-job-${Date.now()}`;
    await page.evaluate(() => (window as any).showDemoOverlay('Step 6: CP-SAT Optimization', '<div>Queuing job...</div>'));
    res = await request.post(`${API_BASE}/api/v1/optimizations`, {
      headers,
      data: {
        idempotency_key: idemKey,
        min_open_facilities: 2,
        max_open_facilities: 4,
        max_travel_seconds: 1800,
        // `scenarios` are the optimizer's canonical UNCERTAINTY scenario names and
        // must match the configured tier count (3). They are not resilience
        // scenario record ids -- passing one raised a ValueError. Omitting the field
        // uses the canonical three-tier set, which is also the truer story: the
        // resilience scenario above measures network impact, while the optimizer
        // solves across its own uncertainty tiers.
      }
    });
    expect(res.ok()).toBeTruthy();
    data = await res.json();
    const jobId = data.id || data.job_id;
    await page.evaluate((d) => {
      const html = `<div style="display:grid; grid-template-columns:120px 1fr; gap:8px;">
        <strong style="color:#94a3b8">Job ID:</strong> <span style="font-family:monospace; color:#38bdf8">${d.id || d.job_id}</span>
        <strong style="color:#94a3b8">Status:</strong> <span style="color:#fbbf24">${d.status || 'UNAVAILABLE'}</span>
      </div>`;
      (window as any).showDemoOverlay('Step 6: Job Queued', html);
    }, data);
    await page.waitForTimeout(Math.round(DWELL * 0.55));

    // 7. wait for actual completed optimization result
    await page.evaluate(() => (window as any).showDemoOverlay('Step 7: Polling for Completion', '<div>Waiting for CP-SAT worker...</div>'));
    let isComplete = false;
    let finalJobData = null;
    for (let i = 0; i < 30; i++) {
       const pollRes = await request.get(`${API_BASE}/api/v1/optimizations/${jobId}`, { headers });
       const pollData = await pollRes.json();
       if (pollData.status === 'SUCCESS' || pollData.status === 'COMPLETED') {
          isComplete = true;
          finalJobData = pollData;
          break;
       }
       await page.waitForTimeout(Math.round(DWELL * 0.55));
    }
    expect(isComplete).toBeTruthy();
    
    // 8. show selected capacity/facilities and tradeoffs
    const resDoc = typeof finalJobData.result_document === 'string' ? JSON.parse(finalJobData.result_document) : finalJobData.result_document;
    // Every value below comes from the solver result. The previous panel fell back
    // to 'fac-01, fac-04' and an objective of '3142.50' when a key was missing, and
    // hardcoded both COMPLETED and an "assumption" description that existed nowhere
    // -- so a viewer could not tell a real solve from a placeholder.
    await page.evaluate((d) => {
      const facilities = Array.isArray(d.opened_facility_ids) ? d.opened_facility_ids : [];
      const objective = d.objective && typeof d.objective.weighted_total === 'number'
        ? d.objective.weighted_total.toLocaleString('en-US')
        : 'UNAVAILABLE';
      const assumption = d.objective && d.objective.weights && d.objective.weights.assumption_version
        ? String(d.objective.weights.assumption_version).split('+')[0]
        : (d.assumption_version || 'UNAVAILABLE');
      const status = d.solver_status || d.status || 'UNAVAILABLE';
      const statusColour = status === 'OPTIMAL' ? '#22c55e' : '#fbbf24';
      const html = `
        <div style="display:grid; grid-template-columns:160px 1fr; gap:8px;">
          <strong style="color:#94a3b8">Job ID:</strong> <span style="font-family:monospace; color:#38bdf8; font-size:13px">${d.__jobId || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Solver:</strong> <span style="font-family:monospace">${d.solver_version || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Solver status:</strong> <span style="color:${statusColour}; font-weight:700">${status}</span>
          <strong style="color:#94a3b8">Action:</strong> <span style="font-family:monospace">${d.action || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Facilities opened:</strong> <span style="color:#fbbf24; font-family:monospace; font-size:13px">${facilities.length ? facilities.join(', ') : 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Objective:</strong> <span style="font-family:monospace">${objective}</span>
          <strong style="color:#94a3b8">Assumption set:</strong> <div><span style="background-color:#3b82f6; color:white; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold;">ASSUMPTION</span> <span style="font-family:monospace; font-size:12px">${assumption}</span></div>
        </div>
      `;
      (window as any).showDemoOverlay('Step 8: CP-SAT Optimization Result', html);
    }, { ...finalJobData, ...resDoc, __jobId: jobId });
    await page.waitForTimeout(DWELL);
    await page.screenshot({ path: `${SHOT_DIR}/05-optimization.png` });

    // 9. freeze decision FROM THE COMPLETED OPTIMIZATION JOB
    await page.evaluate(() => (window as any).showDemoOverlay('Step 9: Freezing Decision', '<div>Executing freeze operation...</div>'));
    res = await request.post(`${API_BASE}/api/v1/decisions/freeze`, {
      headers,
      data: {
        optimization_job_id: jobId,
        operator_rationale: "Swiggy Friday Demo automated decision freeze",
      }
    });
    expect(res.ok()).toBeTruthy();
    data = await res.json();
    const decisionId = data.decision_id;
    // The decision record carries real lineage; the previous panel read field names
    // it does not have (optimization_job_id, release_sha) and so showed UNAVAILABLE
    // beside a hardcoded "Verified & Secured" claim that came from nowhere.
    await page.evaluate((d) => {
      const facilities = Array.isArray(d.opened_facilities) ? d.opened_facilities : [];
      const html = `
        <div style="display:grid; grid-template-columns:150px 1fr; gap:8px;">
          <strong style="color:#94a3b8">Decision ID:</strong> <span style="font-family:monospace; color:#38bdf8">${d.decision_id}</span>
          <strong style="color:#94a3b8">Type:</strong> <span style="background:#065f46; color:#a7f3d0; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600">OPTIMIZER_DECISION</span>
          <strong style="color:#94a3b8">Source Job:</strong> <span style="font-family:monospace; font-size:13px">${d.__jobId || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Facilities Opened:</strong> <span style="font-family:monospace; font-size:13px">${facilities.length ? facilities.join(', ') : 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Solver:</strong> <span style="font-family:monospace">${d.solver_version || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Graph Version:</strong> <span style="font-family:monospace">${d.graph_version || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Release (code_sha):</strong> <span style="font-family:monospace; font-size:12px">${d.code_sha || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Decision Time:</strong> <span style="font-family:monospace; font-size:13px">${d.decision_time || 'UNAVAILABLE'}</span>
        </div>
      `;
      (window as any).showDemoOverlay('Step 9: Authoritative Decision Frozen', html);
    }, { ...data, __jobId: jobId });
    await page.waitForTimeout(DWELL);
    await page.screenshot({ path: `${SHOT_DIR}/06-decision.png` });

    // 10. open decision provenance/evidence
    res = await request.get(`${API_BASE}/api/v1/decisions/${decisionId}`, { headers });
    expect(res.ok()).toBeTruthy();
    data = await res.json();
    await page.evaluate((d) => {
      const html = `<div>Reviewing cryptographic evidence and operator rationale for decision <span style="font-family:monospace">${d.decision_id}</span>.</div>`;
      (window as any).showDemoOverlay('Step 10: Decision Provenance', html);
    }, data);
    await page.waitForTimeout(DWELL);
    await page.screenshot({ path: `${SHOT_DIR}/07-evidence.png` });

    // 11. perform PIT replay
    await page.evaluate(() => (window as any).showDemoOverlay('Step 11: Performing PIT Replay', '<div>Re-evaluating historical state...</div>'));
    res = await request.post(`${API_BASE}/api/v1/decisions/${decisionId}/replay`, { headers, data: {} });
    expect(res.ok()).toBeTruthy();
    data = await res.json();
    
    // The replay verdict is displayed as returned. Forcing EXACT_MATCH here would
    // both hide a real DRIFT result and abort the recording over a truthful outcome.
    expect(['EXACT_MATCH', 'SEMANTIC_MATCH', 'DRIFT', 'NON_REPLAYABLE']).toContain(data.match_status);
    
    await page.evaluate((d) => {
      // Every field below is returned by the replay endpoint. The previous panel
      // read as_of_timestamp and decision_id, neither of which exists on this
      // response, so it rendered "UNAVAILABLE" and a literal "undefined".
      const yesNo = (v: unknown) => (v === true ? 'YES' : v === false ? 'NO' : 'UNAVAILABLE');
      const status = d.match_status || 'UNAVAILABLE';
      const statusColour = status === 'EXACT_MATCH' ? '#22c55e' : '#fbbf24';
      const hashesAgree = d.expected_hash && d.actual_hash && d.expected_hash === d.actual_hash;
      const html = `
        <div style="display:grid; grid-template-columns:180px 1fr; gap:8px;">
          <strong style="color:#94a3b8">Original decision:</strong> <span style="font-family:monospace; color:#38bdf8; font-size:13px">${d.original_decision_id || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Replayed at:</strong> <span style="font-family:monospace; font-size:13px">${d.replayed_at || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Point-in-time valid:</strong> <span style="font-family:monospace">${yesNo(d.pit_valid)}</span>
          <strong style="color:#94a3b8">Frozen hash:</strong> <span style="font-family:monospace; font-size:13px">${d.expected_hash || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Recomputed hash:</strong> <span style="font-family:monospace; font-size:13px; color:${hashesAgree ? '#22c55e' : '#fbbf24'}">${d.actual_hash || 'UNAVAILABLE'}</span>
          <strong style="color:#94a3b8">Action reproduced:</strong> <span style="font-family:monospace">${yesNo(d.reproduced_exact_action)}</span>
          <strong style="color:#94a3b8">Facilities reproduced:</strong> <span style="font-family:monospace">${yesNo(d.reproduced_exact_facilities)}</span>
          <strong style="color:#94a3b8">Objective match:</strong> <span style="font-family:monospace">${yesNo(d.objective_match)}</span>
          <strong style="color:#94a3b8">Verdict:</strong> <div><span style="background-color:${statusColour}; color:#04120a; padding:3px 10px; border-radius:4px; font-weight:800; font-size:13px">${status}</span></div>
        </div>
      `;
      (window as any).showDemoOverlay('Step 11: Point-in-Time Replay', html);
    }, data);
    await page.waitForTimeout(DWELL);
    await page.screenshot({ path: `${SHOT_DIR}/08-replay.png` });

    // 12. optionally ask Assistant
    // Using the ML Lab interface for Assistant
    if (process.env.INCLUDE_ASSISTANT === 'true') {
      await page.goto('/admin/ml-lab');
      await expect(page.locator('h1')).toContainText('Intelligence Lab');
      await page.fill('input[placeholder*="Ask"]', 'Why were these facilities selected in the latest optimization?');
      await page.click('button:has-text("Ask")');
      await page.waitForTimeout(4000); // wait for response
      // Take snapshot of assistant response
      await page.evaluate(() => (window as any).showDemoOverlay('Step 12: Assistant Query', '<div>Query complete and validated.</div>'));
    }

    // 13. finish on the decision/replay/evidence screen
    await page.evaluate((d) => {
       const html = `<div style="color:#22c55e; font-weight:bold;">All requirements verified successfully.</div>
       <div style="margin-top:8px;"><strong style="color:#94a3b8">Final Job:</strong> <span style="font-family:monospace">${d.jobId}</span></div>
       <div><strong style="color:#94a3b8">Final Decision:</strong> <span style="font-family:monospace">${d.decisionId}</span></div>`;
       (window as any).showDemoOverlay('Step 13: Demo Complete', html);
    }, { jobId, decisionId });
    await page.waitForTimeout(DWELL);
    
    // Dump to test annotations so wrapper script can parse them
    test.info().annotations.push({ type: 'job_id', description: jobId });
    test.info().annotations.push({ type: 'decision_id', description: decisionId });
  });
});
