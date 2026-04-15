import { test, expect } from './_fixtures';

test.describe('Voice Comparison', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/compare');
  });

  test('renders comparison page with heading', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Voice Comparison' })).toBeVisible();
  });

  test('voice selection section is present', async ({ page }) => {
    const voiceSelectionHeading = page.locator('text=/Voice Selection/');
    await expect(voiceSelectionHeading).toBeVisible();
  });

  test('text input accepts comparison phrase', async ({ page }) => {
    const textInput = page.locator('textarea').first();
    await expect(textInput).toBeVisible();

    await textInput.fill('This is a test phrase for voice comparison.');
    await expect(textInput).toHaveValue('This is a test phrase for voice comparison.');

    const generateBtn = page.getByRole('button', { name: /Generate All/i });
    await expect(generateBtn).toBeVisible();
  });

  test('history link is accessible from comparison page', async ({ page }) => {
    const historyLink = page.getByRole('link', { name: 'History' });
    await expect(historyLink).toBeVisible();
  });
});
