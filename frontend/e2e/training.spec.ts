import { test, expect } from './_fixtures';

test.describe('Training Studio', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/training');
  });

  test('renders training studio page', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Training Studio' })).toBeVisible();
  });

  test('shows voice profile selection', async ({ page }) => {
    const profileLabel = page.getByText('Voice Profile', { exact: true });
    await expect(profileLabel).toBeVisible({ timeout: 10000 });

    const profileSelect = page.getByRole('combobox').or(page.locator('select')).first();
    await expect(profileSelect).toBeVisible({ timeout: 10000 });
  });

  test('clone voice link navigates to clone page', async ({ page }) => {
    const cloneLink = page.getByRole('link', { name: 'Clone Voice' });
    await expect(cloneLink).toBeVisible();
    await cloneLink.click({ force: true });
    await expect(page).toHaveURL('/clone');
  });

  test('training job management shows profile select', async ({ page }) => {
    const profileSelect = page.locator('select').first();
    await expect(profileSelect).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('heading', { name: 'Training Studio' })).toBeVisible();
  });

  test('history link navigates to history page', async ({ page }) => {
    const historyLink = page.getByRole('link', { name: 'History' });
    await expect(historyLink).toBeVisible();
    await historyLink.click({ force: true });
    await expect(page).toHaveURL('/history');
  });
});
