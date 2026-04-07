import { test as base, expect, Page, Locator } from '@playwright/test';

// Extend base test with custom fixtures
export const test = base.extend<{
  // Custom page fixture with helper methods
  appPage: AppPage;
}>({
  appPage: async ({ page }, use) => {
    const appPage = new AppPage(page);
    await use(appPage);
  },
});

export { expect };

/**
 * Custom Page Object Model for Atlas Vox app
 */
export class AppPage {
  constructor(private page: Page) {}

  // Navigation helpers
  async navigateTo(path: string) {
    await this.page.goto(path);
    await this.page.waitForTimeout(500);
  }

  async navigateToLibrary() {
    await this.page.click('a[href="/library"]');
    await expect(this.page).toHaveURL('/library');
  }

  async navigateToProfiles() {
    await this.page.click('a[href="/profiles"]');
    await expect(this.page).toHaveURL('/profiles');
  }

  async navigateToSynthesis() {
    await this.page.click('a[href="/synthesis"]');
    await expect(this.page).toHaveURL('/synthesis');
  }

  async navigateToTraining() {
    await this.page.click('a[href="/training"]');
    await expect(this.page).toHaveURL('/training');
  }

  async navigateToComparison() {
    await this.page.click('a[href="/compare"]');
    await expect(this.page).toHaveURL('/compare');
  }

  async navigateToProviders() {
    await this.page.click('a[href="/providers"]');
    await expect(this.page).toHaveURL('/providers');
  }

  async navigateToSettings() {
    await this.page.click('a[href="/settings"]');
    await expect(this.page).toHaveURL('/settings');
  }

  async navigateToHelp() {
    await this.page.click('a[href="/help"]');
    await expect(this.page).toHaveURL('/help');
  }

  // Common element selectors
  get loadingIndicator(): Locator {
    return this.page.locator('[data-testid="loading"]').or(this.page.locator('.loading'));
  }

  get errorMessage(): Locator {
    return this.page.locator('[data-testid="error"]').or(this.page.locator('.error'));
  }

  get successMessage(): Locator {
    return this.page.locator('[data-testid="success"]').or(this.page.locator('.success'));
  }

  get modal(): Locator {
    return this.page.locator('[role="dialog"]');
  }

  // Form helpers
  async fillTextInput(selector: string, text: string) {
    const input = this.page.locator(selector);
    await input.fill(text);
    await expect(input).toHaveValue(text);
  }

  async selectOption(selector: string, option: string | number) {
    const select = this.page.locator(selector);
    if (typeof option === 'string') {
      await select.selectOption({ label: option });
    } else {
      await select.selectOption({ index: option });
    }
  }

  async clickButton(name: string | RegExp) {
    const button = this.page.getByRole('button', { name });
    await button.first().click();
  }

  // Modal helpers
  async openModal(triggerSelector: string) {
    await this.page.click(triggerSelector);
    await expect(this.modal).toBeVisible({ timeout: 3000 });
  }

  async closeModal() {
    const closeBtn = this.page.getByRole('button', { name: /close|cancel/i });
    if (await closeBtn.first().isVisible()) {
      await closeBtn.first().click();
    } else {
      await this.page.keyboard.press('Escape');
    }
    await expect(this.modal).not.toBeVisible({ timeout: 3000 });
  }

  // Audio helpers
  async waitForAudioPlayer() {
    const audioPlayer = this.page.locator('audio').or(this.page.locator('[data-testid="audio-player"]'));
    await expect(audioPlayer.first()).toBeVisible({ timeout: 10000 });
    return audioPlayer.first();
  }

  async playAudio() {
    const playBtn = this.page.getByRole('button', { name: /play/i });
    await playBtn.first().click();
    await this.page.waitForTimeout(1000);
  }

  async stopAudio() {
    const stopBtn = this.page.getByRole('button', { name: /stop|pause/i });
    if (await stopBtn.first().isVisible()) {
      await stopBtn.first().click();
    }
  }

  // Synthesis helpers
  async synthesizeText(text: string) {
    await this.navigateToSynthesis();

    const textInput = this.page.locator('textarea').first();
    if (await textInput.isVisible()) {
      await textInput.fill(text);

      const synthButton = this.page.getByRole('button', { name: /synthesize/i });
      if (await synthButton.first().isVisible()) {
        await synthButton.first().click();
        await this.page.waitForTimeout(2000);

        // Wait for either success (audio) or error
        const audio = this.page.locator('audio');
        const error = this.errorMessage;

        await expect(audio.or(error)).toBeVisible({ timeout: 10000 });
        return await audio.isVisible();
      }
    }
    return false;
  }

  // Profile helpers
  async createProfile(name: string, type: 'built-in' | 'custom' | 'clone' = 'built-in') {
    await this.navigateToProfiles();

    const createBtn = this.page.getByRole('button', { name: /create|new|add/i });
    if (await createBtn.first().isVisible()) {
      await createBtn.first().click();
      await expect(this.modal).toBeVisible({ timeout: 3000 });

      // Fill profile name
      const nameInput = this.page.getByPlaceholder('Profile name').or(this.page.getByLabel(/name/i));
      if (await nameInput.first().isVisible()) {
        await nameInput.first().fill(name);
      }

      // Select profile type
      if (type !== 'built-in') {
        const typeOption = this.page.getByText(type === 'custom' ? 'Custom Voice' : 'Voice Clone');
        if (await typeOption.isVisible()) {
          await typeOption.click();
          await this.page.waitForTimeout(300);
        }
      }

      // Submit form
      const submitBtn = this.page.getByRole('button', { name: /create|save|submit/i });
      if (await submitBtn.first().isVisible() && await submitBtn.first().isEnabled()) {
        await submitBtn.first().click();
        await this.page.waitForTimeout(1000);

        // Wait for success or error
        const success = this.successMessage;
        const error = this.errorMessage;

        await expect(success.or(error)).toBeVisible({ timeout: 5000 });
        return await success.isVisible();
      }
    }
    return false;
  }

  // Provider helpers
  async checkProviderHealth() {
    await this.navigateToProviders();

    const healthBtn = this.page.getByRole('button', { name: /health|check|refresh/i });
    if (await healthBtn.first().isVisible()) {
      await healthBtn.first().click();
      await this.page.waitForTimeout(1000);

      // Wait for result
      const loading = this.loadingIndicator;
      const success = this.successMessage;
      const status = this.page.locator('[data-testid="status"]');

      await expect(loading.or(success).or(status)).toBeVisible({ timeout: 10000 });
      return true;
    }
    return false;
  }

  // Theme helpers
  async toggleTheme() {
    const themeToggle = this.page.getByRole('button', { name: /theme|dark|light/i });
    if (await themeToggle.first().isVisible()) {
      const htmlEl = this.page.locator('html');
      const initialClass = await htmlEl.getAttribute('class');

      await themeToggle.first().click();
      await this.page.waitForTimeout(300);

      const newClass = await htmlEl.getAttribute('class');
      return newClass !== initialClass;
    }
    return false;
  }

  // Search helpers
  async searchGlobally(query: string) {
    const searchInput = this.page.getByPlaceholder(/search/i).first();
    if (await searchInput.isVisible()) {
      await searchInput.fill(query);
      await this.page.waitForTimeout(500);

      const results = this.page.locator('[data-testid="search-results"]').or(
        this.page.locator('.search-dropdown')
      );

      if (await results.isVisible()) {
        return results;
      }
    }
    return null;
  }

  // Wait helpers
  async waitForPageLoad() {
    await this.page.waitForLoadState('networkidle');
  }

  async waitForApiResponse(urlPattern: string | RegExp) {
    return this.page.waitForResponse(urlPattern);
  }

  // Utility helpers
  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `screenshots/${name}.png` });
  }

  async mockApiResponse(url: string | RegExp, response: any) {
    await this.page.route(url, route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(response)
      });
    });
  }

  async mockApiError(url: string | RegExp, status: number = 500, message: string = 'Server Error') {
    await this.page.route(url, route => {
      route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify({ message })
      });
    });
  }

  // Accessibility helpers
  async checkKeyboardNavigation() {
    // Tab through focusable elements
    const focusableElements: Locator[] = [];

    for (let i = 0; i < 10; i++) {
      await this.page.keyboard.press('Tab');
      await this.page.waitForTimeout(100);

      const focused = this.page.locator(':focus');
      if (await focused.isVisible()) {
        focusableElements.push(focused);
      }
    }

    return focusableElements.length > 0;
  }

  async checkAriaLabels() {
    const buttons = this.page.getByRole('button');
    const count = await buttons.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const button = buttons.nth(i);
      if (await button.isVisible()) {
        const ariaLabel = await button.getAttribute('aria-label');
        const textContent = await button.textContent();

        if (!ariaLabel && !textContent?.trim()) {
          console.warn(`Button ${i} lacks accessible name`);
          return false;
        }
      }
    }

    return true;
  }

  // Mobile helpers
  async setMobileViewport() {
    await this.page.setViewportSize({ width: 375, height: 667 });
  }

  async setTabletViewport() {
    await this.page.setViewportSize({ width: 768, height: 1024 });
  }

  async setDesktopViewport() {
    await this.page.setViewportSize({ width: 1920, height: 1080 });
  }

  async openMobileMenu() {
    await this.setMobileViewport();

    const mobileMenuToggle = this.page.locator('button').filter({ hasText: /menu|toggle/i });
    if (await mobileMenuToggle.first().isVisible()) {
      await mobileMenuToggle.first().click();
      await this.page.waitForTimeout(300);
      return true;
    }
    return false;
  }
}

/**
 * Custom expect extensions for Atlas Vox
 */
export const customExpect = {
  async toHaveAudio(page: Page) {
    const audio = page.locator('audio').or(page.locator('[data-testid="audio-player"]'));
    await expect(audio.first()).toBeVisible({ timeout: 10000 });
  },

  async toShowLoadingState(page: Page) {
    const loading = page.locator('[data-testid="loading"]').or(page.locator('.loading'));
    await expect(loading).toBeVisible({ timeout: 5000 });
  },

  async toShowError(page: Page, message?: string) {
    const error = page.locator('[data-testid="error"]').or(page.locator('.error'));
    await expect(error.first()).toBeVisible({ timeout: 5000 });

    if (message) {
      await expect(error.first()).toContainText(message);
    }
  },

  async toShowSuccess(page: Page, message?: string) {
    const success = page.locator('[data-testid="success"]').or(page.locator('.success'));
    await expect(success.first()).toBeVisible({ timeout: 5000 });

    if (message) {
      await expect(success.first()).toContainText(message);
    }
  }
};

/**
 * Test data generators
 */
export const testData = {
  profiles: {
    builtIn: {
      name: 'Test Built-in Profile',
      type: 'built-in' as const
    },
    custom: {
      name: 'Test Custom Profile',
      type: 'custom' as const
    },
    clone: {
      name: 'Test Clone Profile',
      type: 'clone' as const
    }
  },

  synthesis: {
    simple: 'Hello world, this is a test.',
    complex: 'This is a more complex sentence with punctuation, numbers like 123, and emphasis!',
    ssml: '<speak><prosody rate="slow">This is slow speech.</prosody></speak>'
  },

  urls: {
    dashboard: '/',
    library: '/library',
    profiles: '/profiles',
    synthesis: '/synthesis',
    training: '/training',
    compare: '/compare',
    providers: '/providers',
    settings: '/settings',
    help: '/help',
    docs: '/docs'
  }
};

/**
 * Common test patterns
 */
export const testPatterns = {
  async testNavigation(page: Page, urls: string[]) {
    for (const url of urls) {
      await page.goto(url);
      await expect(page.locator('body')).toBeVisible();
      await page.waitForTimeout(500);
    }
  },

  async testResponsive(page: Page, testUrl: string = '/') {
    const viewports = [
      { width: 375, height: 667, name: 'mobile' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 1920, height: 1080, name: 'desktop' }
    ];

    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(testUrl);
      await expect(page.locator('body')).toBeVisible();
      await page.waitForTimeout(500);
    }
  },

  async testFormValidation(page: Page, formSelector: string, submitSelector: string) {
    // Try to submit without required fields
    await page.click(submitSelector);
    await page.waitForTimeout(300);

    // Should show validation errors
    const error = page.locator('[data-testid="validation-error"]').or(
      page.locator('.error').or(page.locator('text=required'))
    );

    return await error.first().isVisible();
  },

  async testLoadingStates(page: Page, triggerSelector: string) {
    await page.click(triggerSelector);

    const loading = page.locator('[data-testid="loading"]').or(page.locator('.loading'));
    const result = page.locator('[data-testid="success"]').or(
      page.locator('[data-testid="error"]')
    );

    // Either loading should appear, or result should appear quickly
    await expect(loading.or(result)).toBeVisible({ timeout: 10000 });
  }
};

export default { test, expect, AppPage, customExpect, testData, testPatterns };