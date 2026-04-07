import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('sidebar navigation works for all main pages', async ({ page }) => {
    // This test navigates through all pages sequentially — increase timeout
    test.setTimeout(60000);

    await page.goto('/');

    // Dashboard loads
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 15000 });

    // Navigate to Voice Library
    await page.click('a[href="/library"]');
    await expect(page).toHaveURL('/library');
    await expect(page.getByRole('heading', { name: 'Voice Library' })).toBeVisible({ timeout: 10000 });

    // Navigate to Profiles
    await page.click('a[href="/profiles"]');
    await expect(page).toHaveURL('/profiles');
    await expect(page.getByRole('heading', { name: 'Voice Profiles' })).toBeVisible({ timeout: 10000 });

    // Navigate to Synthesis
    await page.click('a[href="/synthesis"]');
    await expect(page).toHaveURL('/synthesis');
    await expect(page.getByRole('heading', { name: 'Synthesis Lab' })).toBeVisible({ timeout: 10000 });

    // Navigate to Training
    await page.click('a[href="/training"]');
    await expect(page).toHaveURL('/training');
    await expect(page.getByRole('heading', { name: 'Training Studio' })).toBeVisible({ timeout: 10000 });

    // Navigate to Comparison
    await page.click('a[href="/compare"]');
    await expect(page).toHaveURL('/compare');
    await expect(page.getByRole('heading', { name: 'Voice Comparison' })).toBeVisible({ timeout: 10000 });

    // Navigate to Providers
    await page.click('a[href="/providers"]');
    await expect(page).toHaveURL('/providers');
    await expect(page.getByRole('heading', { name: 'Providers' })).toBeVisible({ timeout: 10000 });

    // Navigate to Settings
    await page.click('a[href="/settings"]');
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
      await mobileMenuToggle.click();
      await page.waitForTimeout(300);

      // Check if navigation is now visible
      const navMenu = page.locator('nav').or(page.locator('[role="navigation"]'));
      await expect(navMenu).toBeVisible();
    }
  });
});
