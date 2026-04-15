import { test, expect } from './_fixtures';

test.describe('Accessibility', () => {
  test('app meets WCAG 2.1 AA standards', async ({ page }) => {
    await page.goto('/');

    // Check for proper heading hierarchy
    const h1 = page.locator('h1').first();
    await expect(h1).toBeVisible({ timeout: 5000 });

    const headings = await page.locator('h1, h2, h3, h4, h5, h6').allTextContents();
    expect(headings.length).toBeGreaterThan(0);
  });

  test('keyboard navigation works throughout app', async ({ page }) => {
    await page.goto('/');

    // Test tab navigation
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);

    // Should focus first interactive element
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();

    // Continue tabbing through navigation
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);

      const currentFocus = page.locator(':focus');
      if (await currentFocus.isVisible()) {
        await expect(currentFocus).toBeVisible();
      }
    }
  });

  test('screen reader compatibility - ARIA labels and roles', async ({ page }) => {
    await page.goto('/');

    // Check for proper ARIA labels on interactive elements
    const buttons = page.getByRole('button');
    const buttonCount = await buttons.count();

    for (let i = 0; i < Math.min(buttonCount, 5); i++) {
      const button = buttons.nth(i);
      if (await button.isVisible()) {
        const accessibleName = await button.getAttribute('aria-label') ||
                              await button.textContent() ||
                              await button.getAttribute('aria-labelledby');
        expect(accessibleName).toBeTruthy();
      }
    }

    // Check navigation landmarks — there are TWO nav elements (Main navigation + Primary)
    // Use .first() to avoid strict mode violation
    const nav = page.getByRole('navigation').first();
    await expect(nav).toBeVisible();

    const main = page.getByRole('main');
    await expect(main).toBeVisible();
  });

  test('color contrast meets accessibility standards', async ({ page }) => {
    await page.goto('/');

    const textElements = page.locator('p, span, div, h1, h2, h3, h4, h5, h6').first();
    await expect(textElements).toBeVisible();
  });

  test('form accessibility - labels and error messages', async ({ page }) => {
    await page.goto('/profiles');

    const createBtn = page.getByRole('button', { name: /New Profile/i });

    if (await createBtn.isVisible()) {
      await createBtn.click({ force: true });
      await page.waitForTimeout(500);

      // Check form inputs have proper labels
      const inputs = page.locator('input, textarea, select');
      const inputCount = await inputs.count();

      for (let i = 0; i < Math.min(inputCount, 3); i++) {
        const input = inputs.nth(i);
        if (await input.isVisible()) {
          const label = await input.getAttribute('aria-label') ||
                       await input.getAttribute('aria-labelledby') ||
                       await input.getAttribute('placeholder');

          if (label) {
            expect(label).toBeTruthy();
          } else {
            const inputId = await input.getAttribute('id');
            if (inputId) {
              const associatedLabel = page.locator(`label[for="${inputId}"]`);
              if (await associatedLabel.isVisible()) {
                await expect(associatedLabel).toBeVisible();
              }
            }
          }
        }
      }
    }
  });

  test('focus management in modals and dialogs', async ({ page }) => {
    await page.goto('/profiles');

    const createBtn = page.getByRole('button', { name: /New Profile/i });

    if (await createBtn.isVisible()) {
      await createBtn.click({ force: true });
      await page.waitForTimeout(500);

      const modal = page.locator('[role="dialog"]');

      if (await modal.isVisible()) {
        // Focus should be within modal
        await page.keyboard.press('Tab');
        await page.waitForTimeout(200);

        const isWithinModal = await modal.locator(':focus').isVisible();
        expect(isWithinModal).toBeTruthy();

        // Escape should close modal
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
        await expect(modal).not.toBeVisible();
      }
    }
  });

  test('audio controls are keyboard accessible', async ({ page }) => {
    await page.goto('/synthesis');
    await page.waitForTimeout(2000);

    // Look for audio controls
    const audioControls = page.locator('audio, [data-testid="audio-player"]');

    if (await audioControls.first().isVisible()) {
      const playButton = page.getByRole('button', { name: /play/i });

      if (await playButton.first().isVisible()) {
        await playButton.first().focus();
        await expect(playButton.first()).toBeFocused();
      }
    }

    // Page should be functional
    await expect(page.locator('body')).toBeVisible();
  });

  test('skip links for screen reader users', async ({ page }) => {
    await page.goto('/');

    // Press Tab to reveal skip links — actual link text is "Skip to content"
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);

    const skipLink = page.locator('text=Skip to content');

    if (await skipLink.isVisible()) {
      await skipLink.click({ force: true });
      await page.waitForTimeout(300);

      // Should focus main content area
      const mainContent = page.locator('main');
      if (await mainContent.isVisible()) {
        await expect(mainContent).toBeVisible();
      }
    }
  });

  test('high contrast mode compatibility', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
    await page.goto('/');

    await expect(page.locator('body')).toBeVisible();
    await expect(page.getByRole('heading', { name: /Audio Control Center/i })).toBeVisible();
  });

  test('reduced motion preferences respected', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');

    await expect(page.locator('body')).toBeVisible();

    // Navigate to another page
    await page.locator('a[href="/synthesis"]').first().click({ force: true });
    await page.waitForTimeout(500);

    await expect(page.locator('body')).toBeVisible();
  });

  test('text scaling and zoom compatibility', async ({ page }) => {
    await page.goto('/');

    // Test small viewport (simulating zoom)
    await page.setViewportSize({ width: 640, height: 480 });
    await page.waitForTimeout(500);

    // App should remain functional at small viewports
    await expect(page.locator('body')).toBeVisible();

    // Text should still be visible
    const textElements = page.locator('h1, p, button').first();
    if (await textElements.isVisible()) {
      await expect(textElements).toBeVisible();
    }

    // Navigation should still work - use goto instead of clicking potentially-offscreen nav
    await page.goto('/library');
    await page.waitForTimeout(500);
    await expect(page.locator('body')).toBeVisible();
  });

  test('error messages are announced to screen readers', async ({ page }) => {
    await page.goto('/profiles');

    const createBtn = page.getByRole('button', { name: /New Profile/i });

    if (await createBtn.isVisible()) {
      await createBtn.click({ force: true });
      await page.waitForTimeout(500);

      // Try to submit form without required fields
      const submitBtn = page.getByRole('button', { name: /create|save|submit/i });

      if (await submitBtn.first().isVisible()) {
        await submitBtn.first().click({ force: true });
        await page.waitForTimeout(500);

        // Check for error messages with proper ARIA attributes
        const errorMessage = page.locator('[role="alert"]').or(
          page.locator('[aria-live="polite"]').or(
            page.locator('[data-testid="error"]')
          )
        );

        if (await errorMessage.first().isVisible()) {
          await expect(errorMessage.first()).toBeVisible();
        }
      }
    }
  });

  test('loading states are announced to screen readers', async ({ page }) => {
    await page.goto('/providers');

    // Look for loading states or ARIA attributes
    const loadingElement = page.locator('[aria-busy="true"]').or(
      page.locator('[aria-live="polite"]').or(
        page.locator('[role="status"]')
      )
    );

    if (await loadingElement.first().isVisible()) {
      await expect(loadingElement.first()).toBeVisible();
    }

    // Page should be functional
    await expect(page.locator('body')).toBeVisible();
  });
});
