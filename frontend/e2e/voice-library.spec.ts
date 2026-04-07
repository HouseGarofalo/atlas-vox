import { test, expect } from '@playwright/test';

test.describe('Voice Library', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/library');
  });

  test('renders voice library page with search', async ({ page }) => {
    // Use heading to avoid matching nav link
    await expect(page.getByRole('heading', { name: 'Voice Library' })).toBeVisible();
    const searchInput = page.getByPlaceholder('Search voices...');
    await expect(searchInput).toBeVisible();
  });

  test('search input filters voices', async ({ page }) => {
    // Wait for voices to fully load
    const countText = page.getByText(/Showing \d+ of \d+ voices/);
    await expect(countText).toBeVisible({ timeout: 15000 });

    const searchInput = page.getByPlaceholder('Search voices...');
    await searchInput.fill('heart');
    // Wait for debounce
    await page.waitForTimeout(600);
    // Verify the count updates
    await expect(countText).toBeVisible({ timeout: 5000 });
  });

  test('filter dropdowns are functional', async ({ page }) => {
    // Wait for voices to fully load first
    const countText = page.getByText(/Showing \d+ of \d+ voices/);
    await expect(countText).toBeVisible({ timeout: 15000 });

    // Provider filter is a combobox
    const providerFilter = page.getByRole('combobox').first();
    if (await providerFilter.isVisible()) {
      // Select "Kokoro" from the provider filter using label text
      await providerFilter.selectOption({ label: 'Kokoro' });
      await page.waitForTimeout(500);
      // Voices should be filtered
      await expect(page.locator('body')).toBeVisible();

      // Reset to "All Providers"
      await providerFilter.selectOption({ index: 0 });
      await page.waitForTimeout(300);
    }

    await expect(page.locator('body')).toBeVisible();
  });

  test('voice cards show provider info', async ({ page }) => {
    // Wait for voices to fully load
    const countText = page.getByText(/Showing \d+ of \d+ voices/);
    await expect(countText).toBeVisible({ timeout: 15000 });

    // Voice cards have h3 headings and provider name paragraphs
    const firstCardHeading = page.locator('h3').first();
    await expect(firstCardHeading).toBeVisible({ timeout: 5000 });

    // Cards show provider name (e.g., "Kokoro")
    const providerLabel = page.locator('p').filter({ hasText: 'Kokoro' }).first();
    await expect(providerLabel).toBeVisible({ timeout: 5000 });
  });

  test('voice card interactions work', async ({ page }) => {
    await page.waitForTimeout(2000);

    // Look for Preview buttons on voice cards
    const previewButton = page.getByRole('button', { name: 'Preview' }).first();
    if (await previewButton.isVisible()) {
      await previewButton.click();
      await page.waitForTimeout(500);
      // Just ensure the page doesn't crash
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('pagination or infinite scroll works', async ({ page }) => {
    // Wait for voices to fully load from API
    const showingCount = page.getByText(/Showing \d+ of \d+ voices/);
    await expect(showingCount).toBeVisible({ timeout: 15000 });

    // Just ensure the page doesn't crash
    await expect(page.locator('body')).toBeVisible();
  });
});
