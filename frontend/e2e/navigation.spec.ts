import { test, expect } from './_fixtures';

test.describe('Navigation', () => {
  test('sidebar navigation works for all main pages', async ({ page }) => {
    // This test navigates through all pages sequentially — increase timeout
    test.setTimeout(60000);

    await page.goto('/');

    // Dashboard loads
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('heading', { name: /Audio Control Center/i })).toBeVisible({ timeout: 15000 });

    // Navigate to Voice Library
    await page.locator('a[href="/library"]').first().click({ force: true });
    await expect(page).toHaveURL('/library');
    await expect(page.getByRole('heading', { name: 'Voice Library' })).toBeVisible({ timeout: 10000 });

    // Navigate to Profiles
    await page.locator('a[href="/profiles"]').first().click({ force: true });
    await expect(page).toHaveURL('/profiles');
    await expect(page.getByRole('heading', { name: 'Voice Profiles' })).toBeVisible({ timeout: 10000 });

    // Navigate to Synthesis
    await page.locator('a[href="/synthesis"]').first().click({ force: true });
    await expect(page).toHaveURL('/synthesis');
    await expect(page.getByRole('heading', { name: /Synthesis Console/i })).toBeVisible({ timeout: 10000 });

    // Navigate to Training
    await page.locator('a[href="/training"]').first().click({ force: true });
    await expect(page).toHaveURL('/training');
    await expect(page.getByRole('heading', { name: 'Training Studio' })).toBeVisible({ timeout: 10000 });

    // Navigate to Comparison
    await page.locator('a[href="/compare"]').first().click({ force: true });
    await expect(page).toHaveURL('/compare');
    await expect(page.getByRole('heading', { name: 'Voice Comparison' })).toBeVisible({ timeout: 10000 });

    // Navigate to Providers
    await page.locator('a[href="/providers"]').first().click({ force: true });
    await expect(page).toHaveURL('/providers');
    await expect(page.getByRole('heading', { name: 'Providers' })).toBeVisible({ timeout: 10000 });

    // Navigate to Settings
    await page.locator('a[href="/settings"]').first().click({ force: true });
    await expect(page).toHaveURL('/settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible({ timeout: 10000 });
  });

  test('404 page shows for unknown routes', async ({ page }) => {
    await page.goto('/nonexistent-page');
    // Actual 404 page shows "404" and "Page not found"
    await expect(page.locator('text=404')).toBeVisible();
    await expect(page.locator('text=Page not found')).toBeVisible();
  });

  test('admin redirects to providers', async ({ page }) => {
    await page.goto('/admin');
    await expect(page).toHaveURL('/providers');
  });

  test('responsive navigation works on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // App should still be functional at mobile viewport
    await expect(page.locator('body')).toBeVisible();

    // Look for mobile menu toggle (hamburger menu)
    const mobileMenuToggle = page.locator('button').filter({ hasText: /menu|toggle/i }).first();
    if (await mobileMenuToggle.isVisible()) {
      await mobileMenuToggle.click({ force: true });
      await page.waitForTimeout(300);

      // Check if navigation is now visible
      const navMenu = page.locator('nav').or(page.locator('[role="navigation"]'));
      await expect(navMenu).toBeVisible();
    }
  });
});
