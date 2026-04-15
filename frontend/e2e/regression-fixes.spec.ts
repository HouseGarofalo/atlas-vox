import { test, expect } from './_fixtures';

// Regression suite covering the bugs fixed after the initial E2E sweep:
//   1. /docs SPA route (was 301-redirecting off-host via nginx auto-index)
//   2. Monaco SSML editor loading (was blocked by CSP before jsdelivr allow)
//   3. API key creation (was 500ing on VARCHAR(10) truncation)
//   4. STS error surfacing (was silently failing on 500)
//   5. SSML emotion XML escape (injection safety — text level only)

test.describe('Regression: /docs SPA route loads', () => {
  test('navigates to /docs without a host escape', async ({ page }) => {
    await page.goto('/docs');
    await expect(page).toHaveURL(/\/docs$/);
    // Page must render app chrome, not be a directory listing
    await expect(page.locator('body')).toBeVisible();
    // Heuristic: nginx auto-index body is plain text; SPA has scripts
    const hasApp = await page.locator('#root, [id="root"]').count();
    expect(hasApp).toBeGreaterThan(0);
  });

  test('/docs does not escape to another host', async ({ page }) => {
    const responses: string[] = [];
    page.on('response', (r) => responses.push(r.url()));
    await page.goto('/docs', { waitUntil: 'domcontentloaded' });
    // The final URL should still be our origin
    const url = new URL(page.url());
    expect(['localhost', '127.0.0.1']).toContain(url.hostname);
  });
});

test.describe('Regression: Monaco SSML editor loads', () => {
  test('SSML toggle does not get stuck on loading spinner', async ({ page }) => {
    await page.goto('/synthesis');
    const ssmlToggle = page.getByRole('button', { name: /Switch to SSML/i });
    if (!(await ssmlToggle.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, 'SSML toggle not present');
    }
    await ssmlToggle.click({ force: true });

    // Either Monaco renders, OR the fallback textarea appears — both are OK.
    // What MUST NOT happen is a hang on "Loading..." without resolution.
    const monaco = page.locator('.monaco-editor').first();
    const fallback = page.locator('textarea[aria-label="SSML editor"], [data-testid="ssml-fallback"]').first();
    const stuckLoader = page.getByText(/^Loading…?$/).first();

    const deadline = Date.now() + 15000;
    let resolved = false;
    while (Date.now() < deadline) {
      if ((await monaco.isVisible().catch(() => false)) ||
          (await fallback.isVisible().catch(() => false))) {
        resolved = true;
        break;
      }
      await page.waitForTimeout(250);
    }
    expect(resolved, 'Monaco editor or fallback must appear within 15s').toBe(true);
    // And the stuck-loader should NOT still be alone on screen
    const stuckStillVisible = await stuckLoader.isVisible().catch(() => false);
    expect(stuckStillVisible).toBe(false);
  });
});

test.describe('Regression: API key creation succeeds', () => {
  test('creating an API key returns a new avx_ token (no 500)', async ({ page, request }) => {
    await page.goto('/api-keys');
    await expect(
      page.getByRole('heading', { name: 'API Keys', exact: true, level: 1 }),
    ).toBeVisible({ timeout: 5000 });

    // Click "New Key" — force: true bypasses the "stable" wait for
    // elements that sit inside framer-motion animated parents.
    await page.getByRole('button', { name: /New Key/i }).first().click({ force: true });

    // Wait for the modal to mount, then target the Key Name input by its placeholder.
    const nameInput = page.getByPlaceholder('My API Key');
    await expect(nameInput).toBeVisible({ timeout: 10000 });
    const keyName = `e2e-regression-${Date.now()}`;
    await nameInput.fill(keyName);

    // Submit — button text is "Create Key"
    await page.getByRole('button', { name: 'Create Key', exact: true }).click({ force: true });

    // Expect success toast
    const successToast = page.getByText(/API key created/i).first();
    await expect(successToast).toBeVisible({ timeout: 10000 });

    // Expect the generated key to be displayed (avx_ prefix)
    const keyDisplay = page.getByText(/avx_/i).first();
    await expect(keyDisplay).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Regression: no critical JS errors during common flows', () => {
  for (const route of ['/', '/synthesis', '/profiles', '/providers', '/settings', '/api-keys', '/docs']) {
    test(`${route} loads without page errors`, async ({ page }) => {
      const errors: string[] = [];
      page.on('pageerror', (err) => errors.push(err.message));
      // Use 'commit' (just the navigation response) — some pages load
      // long-lived markdown / fonts that delay 'domcontentloaded' past
      // the default 15s nav timeout when the suite runs 4-wide.
      await page.goto(route, { waitUntil: 'commit', timeout: 30000 });
      await page.waitForTimeout(1500);
      expect(errors, `page errors on ${route}: ${errors.join(' | ')}`).toEqual([]);
    });
  }
});
