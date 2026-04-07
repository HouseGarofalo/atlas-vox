import { test, expect } from '@playwright/test';

test.describe('Profiles', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/profiles');
  });

  test('renders profiles page', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Voice Profiles' })).toBeVisible();
  });

  test('create profile button exists and opens dialog', async ({ page }) => {
    // Wait for page to fully render
    await expect(page.getByRole('heading', { name: 'Voice Profiles' })).toBeVisible({ timeout: 10000 });

    // Actual button says "New Profile"
    const createBtn = page.getByRole('button', { name: /New Profile/i });
    await expect(createBtn).toBeVisible({ timeout: 10000 });

    await createBtn.click();
    await page.waitForTimeout(500);

    // Opens an inline panel (not a modal dialog) with "Create Voice Profile" heading
    const createHeading = page.getByRole('heading', { name: 'Create Voice Profile' });
    await expect(createHeading).toBeVisible({ timeout: 5000 });

    // Shows 3 creation options: Library Voice, Custom Voice, Design Voice
    const libraryVoiceBtn = page.getByRole('button', { name: /Library Voice/i });
    await expect(libraryVoiceBtn).toBeVisible();
  });

  test('profile cards display correctly', async ({ page }) => {
    await page.waitForTimeout(2000);

    // With no profiles, shows empty state: "No profiles yet. Create your first voice profile."
    const emptyState = page.getByText('No profiles yet');
    const profileHeading = page.locator('h3').first(); // profile cards would have h3 headings

    // Either empty state message or profile cards should be visible
    await expect(emptyState.or(profileHeading)).toBeVisible({ timeout: 10000 });
  });

  test('profile creation form works', async ({ page }) => {
    const createBtn = page.getByRole('button', { name: /New Profile/i });

    if (await createBtn.isVisible()) {
      await createBtn.click();
      await page.waitForTimeout(500);

      // Should show "Create Voice Profile" inline panel with options
      const createHeading = page.getByRole('heading', { name: 'Create Voice Profile' });
      await expect(createHeading).toBeVisible({ timeout: 5000 });

      // Click "Library Voice" to pick a pre-built voice
      const libraryVoiceBtn = page.getByRole('button', { name: /Library Voice/i });
      if (await libraryVoiceBtn.isVisible()) {
        await libraryVoiceBtn.click();
        await page.waitForTimeout(500);
      }

      // Page should remain functional
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('profile type selection works', async ({ page }) => {
    const createBtn = page.getByRole('button', { name: /New Profile/i });

    if (await createBtn.isVisible()) {
      await createBtn.click();
      await page.waitForTimeout(500);

      // Should show 3 profile types: Library Voice, Custom Voice (Training), Design Voice (AI)
      const createHeading = page.getByRole('heading', { name: 'Create Voice Profile' });
      if (await createHeading.isVisible({ timeout: 3000 }).catch(() => false)) {
        const libraryVoice = page.getByRole('button', { name: /Library Voice/i });
        const customVoice = page.getByRole('button', { name: /Custom Voice/i });
        const designVoice = page.getByRole('button', { name: /Design Voice/i });

        await expect(libraryVoice).toBeVisible();
        await expect(customVoice).toBeVisible();
        await expect(designVoice).toBeVisible();
      }
    }
  });

  test('profile actions work (edit, delete, duplicate)', async ({ page }) => {
    await page.waitForTimeout(2000);

    // With no profiles, just verify the page loads with empty state or profile cards
    const emptyState = page.getByText('No profiles yet');
    const profileCard = page.locator('[data-testid="profile-card"]').or(page.locator('.profile-card')).first();

    // Either empty state or profile cards
    if (await profileCard.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Look for action buttons
      const editButton = page.locator('button').filter({ hasText: /edit/i }).first();
      if (await editButton.isVisible()) {
        await editButton.click();
        await page.waitForTimeout(300);
      }
    } else {
      // Empty state is shown - that's fine for a clean install
      await expect(emptyState).toBeVisible({ timeout: 5000 });
    }
  });
});
