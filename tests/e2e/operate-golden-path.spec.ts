import { expect, test } from '@playwright/test';

/**
 * The golden path a viewer records.
 *
 * This drives the real page against the real API. It is not a screenshot test
 * and it does not stub anything: if the map engine fails to initialise, if the
 * mission artifact is missing, or if the observation store cannot be read, this
 * fails — which is the point. A demo recorded over a broken golden path is
 * worse than no demo.
 *
 * The assertions are deliberately about HONESTY as much as function. A map that
 * renders is not enough; it has to render the right city, label simulated data
 * as simulated, and refuse to describe a stale reading as current.
 */

const OPERATE = '/demo/operate';

/** MapLibre needs a moment to compile shaders and lay out 11k line features. */
async function waitForMap(page: import('@playwright/test').Page) {
  await expect(page.getByTestId('map-stage')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('[data-map-state="ready"]')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('canvas.maplibregl-canvas')).toBeVisible({ timeout: 30_000 });
  // Let the first paint settle so screenshots are not of a half-drawn frame.
  await page.waitForTimeout(1500);
}

test.describe('OPERATE golden path', () => {
  test('the map is a real engine drawing real Bengaluru geography', async ({ page }) => {
    await page.goto(OPERATE);
    await waitForMap(page);

    // A canvas with non-zero size proves the WebGL context actually initialised,
    // rather than the container merely existing.
    const box = await page.locator('canvas.maplibregl-canvas').boundingBox();
    expect(box?.width ?? 0).toBeGreaterThan(400);
    expect(box?.height ?? 0).toBeGreaterThan(300);

    // The engine is present and controllable, not a picture.
    await expect(page.locator('.maplibregl-ctrl-zoom-in')).toBeVisible();
    await expect(page.locator('.maplibregl-ctrl-zoom-out')).toBeVisible();

    // Attribution is a licence condition, not decoration.
    await expect(page.locator('[data-map-attribution="true"]')).toContainText('OpenStreetMap');
  });

  test('the basemap it loaded is Bengaluru, checked by coordinates', async ({ page }) => {
    // An Andorra extract once shipped under a Bengaluru filename and rendered
    // perfectly. Geography is verified by coordinate, never by a name.
    const response = await page.request.get('/demo/bengaluru-basemap.json');
    expect(response.ok()).toBeTruthy();
    const basemap = await response.json();

    expect(basemap.evidence_class).toBe('PUBLIC_GEOGRAPHIC');
    expect(basemap.zones).toHaveLength(94);
    expect(basemap.bbox.min_lat).toBeGreaterThanOrEqual(12.7);
    expect(basemap.bbox.max_lat).toBeLessThanOrEqual(13.2);
    expect(basemap.bbox.min_lon).toBeGreaterThanOrEqual(77.3);
    expect(basemap.bbox.max_lon).toBeLessThanOrEqual(77.9);
  });

  test('sixteen simulated orders are listed and labelled as simulated', async ({ page }) => {
    await page.goto(OPERATE);
    await waitForMap(page);

    const list = page.getByTestId('order-list');
    await expect(list).toBeVisible();
    // The class must be on the panel itself, so a cropped screenshot still
    // carries it.
    await expect(list).toContainText('SIMULATED');
    await expect(list).toContainText('No customer, merchant or rider exists.');

    const rows = page.locator('[data-order-id]');
    await expect(rows).toHaveCount(16);
    await expect(page.locator('[data-order-id="ORD-001"]')).toBeVisible();
    await expect(page.locator('[data-order-id="ORD-016"]')).toBeVisible();
  });

  test('selecting an order reveals its route and does not overstate it', async ({ page }) => {
    await page.goto(OPERATE);
    await waitForMap(page);

    await page.locator('[data-order-id="ORD-009"]').click();

    const detail = page.getByTestId('order-detail');
    await expect(detail).toBeVisible();
    await expect(detail).toContainText('ORD-009');
    await expect(detail).toContainText('km');
    await expect(detail).toContainText('SIMULATED');

    // The routing is not traffic-aware, and the interface has to say so rather
    // than leaving a number that looks like an ETA unqualified.
    await expect(detail).toContainText('not traffic-aware');

    await expect(page.locator('[data-order-id="ORD-009"][data-selected="true"]')).toBeVisible();

    // Clicking again clears the selection, so a presenter can get back to the
    // whole-network view without reloading.
    await page.locator('[data-order-id="ORD-009"]').click();
    await expect(page.getByTestId('order-detail')).toBeHidden();
  });

  test('the routes drawn are road geometry, not straight lines', async ({ page }) => {
    const response = await page.request.get('/demo/mission-routes.json');
    expect(response.ok()).toBeTruthy();
    const artifact = await response.json();

    expect(artifact.evidence_class).toBe('SIMULATED');
    expect(artifact.orders).toHaveLength(16);
    expect(artifact.routes).toHaveLength(16);
    expect(artifact.traffic_aware).toBe(false);

    for (const route of artifact.routes) {
      // Two vertices between two distinct places is a straight line.
      expect(route.geometry.length).toBeGreaterThan(2);
      expect(route.distance_m).toBeGreaterThan(0);
      for (const [lon, lat] of route.geometry) {
        expect(lat).toBeGreaterThanOrEqual(12.7);
        expect(lat).toBeLessThanOrEqual(13.2);
        expect(lon).toBeGreaterThanOrEqual(77.3);
        expect(lon).toBeLessThanOrEqual(77.9);
      }
    }
  });

  test('live context names every source and never claims more than it has', async ({ page }) => {
    await page.goto(OPERATE);
    await waitForMap(page);

    const panel = page.getByTestId('live-context-panel');
    await expect(panel).toBeVisible();

    // Every source the demo shows, with its provenance.
    await expect(panel.locator('[data-source="Traffic"]')).toContainText('PROVIDER_ESTIMATED');
    await expect(panel.locator('[data-source="Weather"]')).toContainText('PUBLIC_OFFICIAL');
    await expect(panel.locator('[data-source="Network geography"]')).toContainText(
      'PUBLIC_GEOGRAPHIC',
    );
    await expect(panel.locator('[data-source="Delivery mission"]')).toContainText('SIMULATED');

    // The word beside a provider must follow its freshness, never be hardcoded
    // to something reassuring.
    const trafficState = await panel
      .locator('[data-source="Traffic"]')
      .getAttribute('data-freshness');
    expect(['FRESH', 'DEGRADED', 'STALE', 'UNAVAILABLE']).toContain(trafficState);

    const trafficRow = panel.locator('[data-source="Traffic"]');
    if (trafficState === 'FRESH') {
      await expect(trafficRow).toContainText('CURRENT');
    } else if (trafficState === 'DEGRADED') {
      await expect(trafficRow).toContainText('RECENT');
    } else if (trafficState === 'STALE') {
      await expect(trafficRow).toContainText('LAST KNOWN');
    } else {
      await expect(trafficRow).toContainText('UNAVAILABLE');
      await expect(trafficRow).toContainText('no observation recorded');
    }
  });

  test('the page states what is real without the narration having to', async ({ page }) => {
    await page.goto(OPERATE);
    await waitForMap(page);

    // A single still frame from the recording must carry this.
    const body = page.locator('body');
    await expect(body).toContainText('public geographic evidence');
    await expect(body).toContainText('provider-estimated');
    await expect(body).toContainText('simulated');
  });

  test('no credential is exposed to the browser', async ({ page }) => {
    await page.goto(OPERATE);
    await waitForMap(page);

    const html = await page.content();
    // Provider keys must never reach client HTML; the browser reads normalized
    // state from our API and never calls a provider directly.
    expect(html).not.toMatch(/api\.tomtom\.com/i);
    expect(html).not.toMatch(/[?&]key=/i);
    expect(html).not.toMatch(/service_role/i);
  });
});
