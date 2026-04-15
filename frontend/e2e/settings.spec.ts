import { test, expect } from './_fixtures';

test.describe('Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings');
  });

  test('renders settings page', async ({ page }) => {
    await expect(page.getByRole('heading', { level: 1, name: 'Settings' })).toBeVisible();
  });

  test('theme toggle changes class on html element', async ({ page }) => {
    const themeToggle = page.getByRole('button', { name: /Toggle theme|Switch to/i }).first();
    await expect(themeToggle).toBeVisible();

    const htmlEl = page.locator('html');
    const initialClass = await htmlEl.getAttribute('class') || '';

    await themeToggle.click({ force: true });
    await page.waitForTimeout(300);

    const newClass = await htmlEl.getAttribute('class') || '';
    expect(newClass).not.toBe(initialClass);

    await themeToggle.click({ force: true });
    await page.waitForTimeout(300);

    const finalClass = await htmlEl.getAttribute('class') || '';
    expect(finalClass).toBe(initialClass);
  });

  test('audio settings section is present', async ({ page }) => {
    const defaultsHeading = page.getByRole('heading', { name: 'Defaults' });
    await expect(defaultsHeading).toBeVisible();

    const audioFormatLabel = page.getByText('Default Audio Format');
    await expect(audioFormatLabel).toBeVisible();

    const audioFormatSelect = page.locator('select').filter({ has: page.locator('option', { hasText: 'WAV' }) });
    await expect(audioFormatSelect).toBeVisible();
  });

  test('default provider can be changed', async ({ page }) => {
    const providerLabel = page.getByText('Default Provider');
    await expect(providerLabel).toBeVisible();

    const providerSelect = page.locator('select').filter({ has: page.locator('option', { hasText: 'Kokoro' }) });
    await expect(providerSelect).toBeVisible();

    await providerSelect.selectOption({ label: 'Piper' });
    await page.waitForTimeout(300);
  });

  test('API keys link navigates to API keys page', async ({ page }) => {
    const apiKeysLink = page.getByRole('link', { name: 'API Keys' });
    await expect(apiKeysLink).toBeVisible();

    await apiKeysLink.click({ force: true });
    await expect(page).toHaveURL('/api-keys');
  });
});
