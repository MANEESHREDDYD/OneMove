import { test, expect, chromium, type BrowserContext } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const SUPABASE_URL = process.env.SUPABASE_URL || "http://127.0.0.1:54321";
const ANON_KEY = process.env.SUPABASE_ANON_KEY || "mock_anon_key";
const LOCAL_SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || "mock_service_key";
const FAIL_ON_MISSING = process.env.FAIL_ON_MISSING_SUPABASE === "true";

let study_id = '';
let assignment_id = '';
let test_token = '';
let user_id = '';
let test_email = '';
let test_password = '';

test.beforeAll(async () => {
    try {
        const ping = await fetch(`${SUPABASE_URL}/rest/v1/`, { headers: { apikey: ANON_KEY }, signal: AbortSignal.timeout(2000) });
        if (!ping.ok && ping.status >= 500) {
            if (FAIL_ON_MISSING) throw new Error("Supabase service unavailable in release validation mode");
            return;
        }
    } catch (e) {
        if (FAIL_ON_MISSING) throw new Error(`Supabase connection failed in release validation mode: ${e}`);
        return;
    }

    test_email = "e2e_mkt_pers_" + Date.now() + "@onemove.com";
    test_password = "password123!";
    
    const signupRes = await fetch(`${SUPABASE_URL}/auth/v1/signup`, {
        method: 'POST',
        headers: { 'apikey': ANON_KEY, 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: test_email, password: test_password })
    });
    
    const user = await signupRes.json();
    if (!user.user) {
        if (FAIL_ON_MISSING) throw new Error("Failed to create test user: " + JSON.stringify(user));
        return;
    }
    
    test_token = user.access_token;
    user_id = user.user.id;

    const srv_headers = {
        "apikey": LOCAL_SERVICE_KEY,
        "Authorization": `Bearer ${LOCAL_SERVICE_KEY}`,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    };

    // 1. Create Study
    const studyRes = await fetch(`${SUPABASE_URL}/rest/v1/studies`, {
        method: 'POST',
        headers: srv_headers,
        body: JSON.stringify({
            city: "Bengaluru",
            started_at: new Date().toISOString(),
            protocol_version: "1.0",
            study_phase: "DRY_RUN",
            status: "planned"
        })
    });
    const study = await studyRes.json();
    study_id = study[0].id;

    // 2. Create Participant
    await fetch(`${SUPABASE_URL}/rest/v1/participants`, {
        method: 'POST',
        headers: srv_headers,
        body: JSON.stringify({ id: user_id, external_id: "ext_mkt_" + Date.now(), hash_key_version: "v1" })
    });

    // 3. Assign OBSERVER Role
    await fetch(`${SUPABASE_URL}/rest/v1/participant_roles`, {
        method: 'POST',
        headers: srv_headers,
        body: JSON.stringify({ participant_id: user_id, study_id, role: "OBSERVER" })
    });

    // 4. Create Active Assignment (SWIGGY / FOOD / ANCHOR)
    const assignRes = await fetch(`${SUPABASE_URL}/rest/v1/assignments`, {
        method: 'POST',
        headers: srv_headers,
        body: JSON.stringify({
            study_id,
            participant_id: user_id,
            zone_cluster: "Indiranagar",
            platform: "SWIGGY",
            intent: "FOOD",
            protocol: "ANCHOR",
            status: "ACTIVE"
        })
    });
    const assignment = await assignRes.json();
    assignment_id = assignment[0].id;
});

test.describe('Marketplace Probe Persistent Offline Profile E2E', () => {
  test('should persist observation across real persistent browser process restart and sync 1 row online', async () => {
    if (!study_id || !assignment_id) {
        if (FAIL_ON_MISSING) {
            throw new Error("Release gate failure: Supabase test setup failed to create study and assignment");
        }
        test.skip(true, "Supabase environment unreachable or credentials missing");
        return;
    }

    const userDataDir = path.join(process.cwd(), '.test_user_data_mkt_' + Date.now());
    let context: BrowserContext | undefined;
    
    try {
        // Phase 1: Launch Persistent Context, Go Offline, Submit Observation
        context = await chromium.launchPersistentContext(userDataDir, { headless: true });
        let page = context.pages()[0] || await context.newPage();

        await page.goto('http://localhost:3001/');
        await page.getByLabel('Email').fill(test_email);
        await page.getByLabel('Password').fill(test_password);
        await page.getByRole('button', { name: 'Sign in' }).click();
        await expect(page.getByRole('heading', { name: 'ZonePilot Observatory' })).toBeVisible();

        await page.goto(`http://localhost:3001/capture?study_id=${study_id}&assignment_id=${assignment_id}`);
        
        // Go offline
        await context.setOffline(true);
        
        await page.selectOption('select', { label: 'Available' });
        await page.locator('text=ETA Low (min)').locator('..').locator('input').fill('15');
        await page.locator('text=ETA High (min)').locator('..').locator('input').fill('20');
        await page.locator('text=Option Count').locator('..').locator('input').fill('12');
        await page.locator('text=Basket Price').locator('..').locator('input').fill('280.00');
        
        await page.click('button[type="submit"]');
        await page.waitForSelector('[data-testid="outbox-status"]');
        
        // Close persistent context completely to simulate browser/process restart
        await context.close();
        context = undefined;

        // Phase 2: Relaunch SAME user data directory, restore the app origin, then
        // go offline before verifying IndexedDB persistence. A fresh browser page
        // cannot navigate to the origin when its context starts offline.
        context = await chromium.launchPersistentContext(userDataDir, { headless: true });
        page = context.pages()[0] || await context.newPage();

        await page.goto('http://localhost:3001/');
        await context.setOffline(true);
        
        // Inspect IndexedDB outbox key in offline state
        const pendingCount = await page.evaluate(async () => {
            return new Promise((resolve) => {
                const req = indexedDB.open('keyval-store');
                req.onsuccess = () => {
                    const db = req.result;
                    if (!db.objectStoreNames.contains('keyval')) {
                        resolve(0);
                        return;
                    }
                    const tx = db.transaction('keyval', 'readonly');
                    const store = tx.objectStore('keyval');
                    const getReq = store.get('zonepilot_outbox');
                    getReq.onsuccess = () => {
                        const val = getReq.result || [];
                        resolve(val.length);
                    };
                    getReq.onerror = () => resolve(0);
                };
                req.onerror = () => resolve(0);
            });
        });

        expect(pendingCount).toBeGreaterThanOrEqual(1);

        // Phase 3: Reconnect Online & Trigger Sync
        await context.setOffline(false);
        const syncResponsePromise = page.waitForResponse((response) =>
            response.url().endsWith('/api/events') && response.request().method() === 'POST'
        );
        await page.goto(`http://localhost:3001/capture?study_id=${study_id}&assignment_id=${assignment_id}`);
        const syncResponse = await syncResponsePromise;
        const syncBody = await syncResponse.text();
        expect(syncResponse.status(), `Outbox sync failed: ${syncBody}`).toBe(201);

        // Phase 4: Verify PostgREST database row
        const probeRes = await fetch(`${SUPABASE_URL}/rest/v1/probe_observations?assignment_id=eq.${assignment_id}`, {
            headers: {
                "apikey": ANON_KEY,
                "Authorization": `Bearer ${test_token}`
            }
        });
        const data = await probeRes.json();
        
        expect(data.length).toBe(1);
        expect(data[0].platform).toBe('SWIGGY');
        expect(data[0].protocol).toBe('ANCHOR');
        expect(data[0].eta_low_min).toBe(15);
        expect(data[0].eta_high_min).toBe(20);

        await context.close();
        context = undefined;
    } finally {
        await context?.close();
        fs.rmSync(userDataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
    }
  });
});
