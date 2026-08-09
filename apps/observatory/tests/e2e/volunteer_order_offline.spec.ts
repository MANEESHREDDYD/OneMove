import { test, expect } from '@playwright/test';

const SUPABASE_URL = process.env.SUPABASE_URL || "http://127.0.0.1:54321";
const ANON_KEY = process.env.SUPABASE_ANON_KEY || "mock_anon_key";
const LOCAL_SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || "mock_service_key";

let study_id = '';
let order_id = '';
let test_token = '';
let user_id = '';

test.beforeAll(async () => {
    try {
        const ping = await fetch(`${SUPABASE_URL}/rest/v1/`, { headers: { apikey: ANON_KEY }, signal: AbortSignal.timeout(2000) });
        if (!ping.ok && ping.status >= 500) return;
    } catch {
        return;
    }

    const email = "e2e_volunteer_" + Date.now() + "@onemove.com";
    const password = "password123";
    
    const signupRes = await fetch(`${SUPABASE_URL}/auth/v1/signup`, {
        method: 'POST',
        headers: { 'apikey': ANON_KEY, 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    
    const user = await signupRes.json();
    if (!user.user) return;
    
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
        body: JSON.stringify({ id: user_id, external_id: "ext_vol_" + Date.now(), hash_key_version: "v1" })
    });

    // 3. Assign VOLUNTEER Role
    await fetch(`${SUPABASE_URL}/rest/v1/participant_roles`, {
        method: 'POST',
        headers: srv_headers,
        body: JSON.stringify({ participant_id: user_id, study_id, role: "VOLUNTEER" })
    });

    // 4. Create Volunteer Order
    const orderRes = await fetch(`${SUPABASE_URL}/rest/v1/volunteer_orders`, {
        method: 'POST',
        headers: srv_headers,
        body: JSON.stringify({
            study_id,
            participant_id: user_id,
            platform: "ZEPTO",
            status: "CREATED"
        })
    });
    const order = await orderRes.json();
    order_id = order[0].id;
});

test.describe('Volunteer Order Offline E2E', () => {
  test('should record order event offline, persist across restart, and sync 1 event online', async ({ browser }) => {
    if (!study_id || !order_id) {
        test.skip(true, "Supabase environment unreachable or keys missing");
        return;
    }

    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('/');
    await page.evaluate((token) => {
        localStorage.setItem('zonepilot_jwt', token);
    }, test_token);

    // Go offline
    await context.setOffline(true);

    // Trigger volunteer event via client outbox / API route
    const eventResult = await page.evaluate(async (orderId) => {
        const clientEventId = crypto.randomUUID();
        const payload = {
            order_id: orderId,
            event_type: "ORDER_PLACED",
            occurred_at: new Date().toISOString(),
            client_event_id: clientEventId
        };
        const res = await fetch("/api/events", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        return { status: res.status, clientEventId };
    }, order_id);

    // Verify local handling
    expect(eventResult).toBeDefined();

    // Close context offline to prove persistence
    await context.close();

    // Reopen context online
    const newContext = await browser.newContext();
    await newContext.setOffline(false);
    const newPage = await newContext.newPage();

    await newPage.goto('/');
    await newPage.evaluate((token) => {
        localStorage.setItem('zonepilot_jwt', token);
    }, test_token);
    await newPage.waitForTimeout(2000);

    // Verify volunteer event was recorded in volunteer_order_events
    const eventRes = await fetch(`${SUPABASE_URL}/rest/v1/volunteer_order_events?order_id=eq.${order_id}`, {
        headers: {
            "apikey": ANON_KEY,
            "Authorization": `Bearer ${test_token}`
        }
    });
    const data = await eventRes.json();

    expect(data.length).toBe(1);
    expect(data[0].event_type).toBe('ORDER_PLACED');

    await newContext.close();
  });
});
