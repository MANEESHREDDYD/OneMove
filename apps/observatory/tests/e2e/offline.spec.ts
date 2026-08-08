import { test, expect } from '@playwright/test';

const SUPABASE_URL = "http://127.0.0.1:54321";
const ANON_KEY = process.env.SUPABASE_ANON_KEY || "sb_publishable" + "_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH";
const LOCAL_SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || "sb_secret" + "_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz";

let order_id = '';
let test_token = '';

test.beforeAll(async () => {
    const email = "e2e_offline_" + Date.now() + "@onemove.com";
    const password = "password123";
    
    let res = await fetch(`${SUPABASE_URL}/auth/v1/signup`, {
        method: 'POST',
        headers: { 'apikey': ANON_KEY, 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    
    const user = await res.json();
    if (!user.user) {
        throw new Error("Failed to create user: " + JSON.stringify(user));
    }
    test_token = user.access_token;
    const user_id = user.user.id;

    const srv_headers = {
        "apikey": LOCAL_SERVICE_KEY,
        "Authorization": `Bearer ${LOCAL_SERVICE_KEY}`,
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    };

    let studyRes = await fetch(`${SUPABASE_URL}/rest/v1/studies`, {
        method: 'POST',
        headers: srv_headers,
        body: JSON.stringify({
            city: "Bengaluru",
            started_at: "2026-08-01T00:00:00Z",
            protocol_version: "1.0",
            status: "planned"
        })
    });
    const study = await studyRes.json();
    const study_id = study[0].id;

    await fetch(`${SUPABASE_URL}/rest/v1/participants`, {
        method: 'POST',
        headers: srv_headers,
        body: JSON.stringify({ id: user_id, external_id: "ext_" + Date.now(), hash_key_version: "v1" })
    });

    let orderRes = await fetch(`${SUPABASE_URL}/rest/v1/volunteer_orders`, {
        method: 'POST',
        headers: srv_headers,
        body: JSON.stringify({ study_id, participant_id: user_id })
    });
    const order = await orderRes.json();
    order_id = order[0].id;
});

test.describe('Offline Outbox Behavior', () => {
  test('should persist observation when offline and sync when online', async ({ page, context }) => {
    
    await page.goto('/');

    await page.evaluate((token) => {
        localStorage.setItem('zonepilot_jwt', token);
    }, test_token);

    await page.goto(`/capture?order_id=${order_id}`);
    
    await context.setOffline(true);
    
    await page.selectOption('select', { label: 'Available' });
    await page.locator('text=ETA Low (min)').locator('..').locator('input').fill('20');
    await page.locator('text=ETA High (min)').locator('..').locator('input').fill('25');
    await page.locator('text=Option Count').locator('..').locator('input').fill('15');
    await page.locator('text=Basket Price').locator('..').locator('input').fill('350.00');
    
    await page.click('button[type="submit"]');
    
    await page.waitForSelector('[data-testid="outbox-status"]');
    
    await context.setOffline(false);
    await page.waitForTimeout(1000);
    await page.reload();
    await page.waitForTimeout(3000);
    
    const res = await fetch(`${SUPABASE_URL}/rest/v1/volunteer_order_events?order_id=eq.${order_id}`, {
        headers: {
            "apikey": ANON_KEY,
            "Authorization": `Bearer ${test_token}`
        }
    });
    const data = await res.json();
    
    expect(data.length).toBe(1);
    expect(data[0].event_type).toBe('PROBE');
    expect(data[0].payload.etaLow).toBe('20');
  });
});
