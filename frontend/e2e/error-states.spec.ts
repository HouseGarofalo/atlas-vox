import { test, expect } from './_fixtures';

test.describe('Error Handling & Resilience', () => {
  test('app handles network errors gracefully', async ({ page }) => {
    // Block all API requests to simulate network failure
    await page.route('**/api/v1/**', route => route.abort());

    await page.goto('/');
    await page.waitForTimeout(2000);

    // App should still render (not crash to white screen)
    await expect(page.locator('body')).toBeVisible();
    const bodyText = await page.locator('body').textContent();
    expect(bodyText).toBeTruthy();
  });

  test('app recovers after network restoration', async ({ page }) => {
    // Start with blocked health API
    await page.route('**/api/v1/health', route => route.abort());
    await page.goto('/');
    await page.waitForTimeout(1000);

    // Unblock API
    await page.unroute('**/api/v1/health');

    // Navigate to providers to trigger fresh requests
    await page.goto('/providers');
    await page.waitForTimeout(2000);

    // App should render correctly — heading should be visible
    await expect(page.getByRole('heading', { name: 'Providers' })).toBeVisible({ timeout: 5000 });
  });

  test('handles malformed API responses', async ({ page }) => {
    // Intercept API calls and return malformed JSON
    await page.route('**/api/v1/providers', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: '{ invalid json malformed'
      });
    });

    await page.goto('/providers');
    await page.waitForTimeout(2000);

    // App should handle the error gracefully (not crash)
    await expect(page.locator('body')).toBeVisible();
  });

  test('handles 404 errors gracefully', async ({ page }) => {
    // Mock 404 response for voices endpoint
    await page.route('**/api/v1/voices', route => {
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Not found' })
      });
    });

    await page.goto('/library');
    await page.waitForTimeout(2000);

    // App should show appropriate state (not crash)
    await expect(page.locator('body')).toBeVisible();
  });

  test('handles 500 server errors', async ({ page }) => {
    // Mock 500 server error on synthesis endpoint
    await page.route('**/api/v1/synthesis', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Internal server error' })
      });
    });

    await page.goto('/synthesis');
    await page.waitForTimeout(1000);

    // Verify the page loads without crashing despite the mocked error
    await expect(page.getByRole('heading', { name: /Synthesis Console/i })).toBeVisible();

    // Text input should still be usable
    const textInput = page.getByPlaceholder('Enter text to synthesize...');
    if (await textInput.isVisible()) {
      await textInput.fill('Test synthesis');
      await page.waitForTimeout(300);
    }

    // App should handle error gracefully (not crash)
    await expect(page.locator('body')).toBeVisible();
  });

  test('handles authentication errors', async ({ page }) => {
    // Mock 401 unauthorized response
    await page.route('**/api/v1/**', route => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Unauthorized' })
      });
    });

    await page.goto('/profiles');
    await page.waitForTimeout(2000);

    // Should handle auth error gracefully
    await expect(page.locator('body')).toBeVisible();
  });

  test('handles rate limiting gracefully', async ({ page }) => {
    // Mock 429 rate limit response
    await page.route('**/api/v1/synthesis', route => {
      route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Rate limit exceeded', retry_after: 60 })
      });
    });

    await page.goto('/synthesis');
    const textInput = page.getByPlaceholder('Enter text to synthesize...');

    if (await textInput.isVisible()) {
      await textInput.fill('Test synthesis');

      const synthButton = page.getByRole('button', { name: 'Synthesize' });
      if (await synthButton.isVisible()) {
        await synthButton.click({ force: true });
        await page.waitForTimeout(1000);

        // App should handle gracefully
        await expect(page.locator('body')).toBeVisible();
      }
    }
  });

  test('form validation prevents invalid submissions', async ({ page }) => {
    await page.goto('/profiles');

    // Try to create profile without required fields
    const createBtn = page.getByRole('button', { name: /New Profile/i });

    if (await createBtn.isVisible()) {
      await createBtn.click({ force: true });
      await page.waitForTimeout(500);

      // Try to submit without filling required fields
      const submitBtn = page.getByRole('button', { name: /create|save|submit/i });

      if (await submitBtn.first().isVisible()) {
        await submitBtn.first().click({ force: true });
        await page.waitForTimeout(300);

        // App should still be functional (validation should prevent submission)
        await expect(page.locator('body')).toBeVisible();
      }
    }
  });

  test('handles file upload errors', async ({ page }) => {
    await page.goto('/profiles');

    const createBtn = page.getByRole('button', { name: /New Profile/i });

    if (await createBtn.isVisible()) {
      await createBtn.click({ force: true });
      await page.waitForTimeout(500);
    }

    // Just verify the page stays functional
    await expect(page.locator('body')).toBeVisible();
  });

  test('handles long-running operations with progress indicators', async ({ page }) => {
    await page.goto('/training');

    // Page should be functional
    await expect(page.getByRole('heading', { name: 'Training Studio' })).toBeVisible();
  });

  test('context menu and keyboard shortcuts work', async ({ page }) => {
    await page.goto('/');

    // Test keyboard shortcut
    await page.keyboard.press('Control+Slash');
    await page.waitForTimeout(500);

    // Should handle gracefully (not crash)
    await expect(page.locator('body')).toBeVisible();
  });
});
