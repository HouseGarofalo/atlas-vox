import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('app loads successfully', async ({ page }) => {
    await page.goto('/');

    // Basic app should load
    await expect(page.locator('body')).toBeVisible();

    // Should have a title
    const title = await page.title();
    expect(title).toBeTruthy();

    // Should not show any critical error
    const criticalError = page.locator('text=Application Error').or(
      page.locator('text=Something went wrong')
    );
    await expect(criticalError).not.toBeVisible();
  });

  test('main navigation is present', async ({ page }) => {
    await page.goto('/');

    // Should have navigation links
    const navLinks = page.locator('nav a').or(page.locator('a[href^="/"]'));
    const linkCount = await navLinks.count();

    expect(linkCount).toBeGreaterThan(0);
  });

  test('can navigate to key pages without errors', async ({ page }) => {
    const routes = ['/', '/library', '/profiles', '/synthesis', '/providers'];

    for (const route of routes) {
      await page.goto(route);

      // Page should load
      await expect(page.locator('body')).toBeVisible();

      // No JavaScript errors
      const errors: string[] = [];
      page.on('pageerror', error => errors.push(error.message));

      await page.waitForTimeout(1000);
      expect(errors).toEqual([]);
    }
  });

  test('app has basic responsive design', async ({ page }) => {
    await page.goto('/');

    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('body')).toBeVisible();

    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect(page.locator('body')).toBeVisible();
  });

  test('app handles API errors gracefully', async ({ page }) => {
    // Block API requests
    await page.route('**/api/v1/**', route => route.abort());

    await page.goto('/');

    // App should still render
    await expect(page.locator('body')).toBeVisible({ timeout: 10000 });

    // Should not show white screen of death
    const bodyText = await page.locator('body').textContent();
    expect(bodyText).toBeTruthy();
  });
});

test.describe('Critical User Flows - Smoke Test', () => {
  test('can access voice library', async ({ page }) => {
    await page.goto('/library');

    await expect(page.getByRole('heading', { name: /Voice Library|Library/i }).first()).toBeVisible({ timeout: 5000 });
  });

  test('can access synthesis page', async ({ page }) => {
    await page.goto('/synthesis');

    // Should have text input for synthesis
    const textInput = page.locator('textarea').or(page.locator('input[type="text"]'));
    await expect(textInput.first()).toBeVisible({ timeout: 5000 });
  });

  test('can access profiles page', async ({ page }) => {
    await page.goto('/profiles');

    await expect(page.locator('text=Profile').first()).toBeVisible({ timeout: 5000 });
  });

  test('can access providers page', async ({ page }) => {
    await page.goto('/providers');

    await expect(page.locator('text=Provider').first()).toBeVisible({ timeout: 5000 });
  });
});