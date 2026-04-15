/**
 * Shared Playwright fixtures for Atlas Vox E2E.
 *
 * Wraps the default `test` export with a `page` fixture that — before any
 * navigation — registers an init script to kill CSS & canvas animations.
 * Without this, the AudioReactiveBackground canvas and framer-motion
 * transitions keep elements permanently non-stable, and Playwright's
 * click-stability wait times out on otherwise-clickable elements.
 *
 * Import from here instead of `@playwright/test`:
 *
 *   import { test, expect } from './_fixtures';
 */
import { test as base, expect } from '@playwright/test';

const DISABLE_ANIM_SCRIPT = `
  (() => {
    if (window.__avoxAnimKilled) return;
    window.__avoxAnimKilled = true;

    const inject = () => {
      if (document.getElementById('__avox-anim-kill')) return;
      const s = document.createElement('style');
      s.id = '__avox-anim-kill';
      s.textContent = \`
        *, *::before, *::after {
          animation-duration: 0s !important;
          animation-delay: 0s !important;
          transition-duration: 0s !important;
          transition-delay: 0s !important;
          scroll-behavior: auto !important;
        }
        canvas[aria-hidden="true"],
        [data-audio-reactive-bg],
        .audio-reactive-background {
          display: none !important;
        }
      \`;
      (document.head || document.documentElement).appendChild(s);
    };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', inject, { once: true });
    } else {
      inject();
    }

  })();
`;

export const test = base.extend({
  page: async ({ page }, use) => {
    await page.addInitScript({ content: DISABLE_ANIM_SCRIPT });
    await use(page);
  },
});

export { expect };
