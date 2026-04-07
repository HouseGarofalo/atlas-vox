# Atlas Vox E2E Tests

Comprehensive end-to-end tests for the Atlas Vox frontend using Playwright.

## Setup

1. Install Playwright (if not already installed):
   ```bash
   npm install -D @playwright/test
   ```

2. Install browser binaries:
   ```bash
   npm run test:e2e:install
   ```

## Running Tests

### All Tests
```bash
npm run test:e2e
```

### Interactive UI Mode
```bash
npm run test:e2e:ui
```

### Debug Mode (Step through tests)
```bash
npm run test:e2e:debug
```

### View Test Report
```bash
npm run test:e2e:report
```

### Specific Test Files
```bash
# Run only navigation tests
npx playwright test navigation

# Run only synthesis tests  
npx playwright test synthesis

# Run tests matching pattern
npx playwright test --grep "profile"
```

## Test Coverage

### Core Functionality Tests

- **`navigation.spec.ts`** - Sidebar navigation, routing, 404 handling
- **`dashboard.spec.ts`** - Dashboard widgets, quick actions, system status
- **`voice-library.spec.ts`** - Voice browsing, search, filtering, playback
- **`synthesis.spec.ts`** - Text-to-speech synthesis, SSML editing, audio generation
- **`profiles.spec.ts`** - Profile creation, management, voice cloning workflow
- **`training.spec.ts`** - Voice training, progress monitoring, model management
- **`comparison.spec.ts`** - Voice comparison, A/B testing, scoring
- **`providers.spec.ts`** - Provider management, health checks, configuration
- **`settings.spec.ts`** - App settings, theme toggle, preferences persistence
- **`help-docs.spec.ts`** - Help system, documentation, search functionality

### Quality Assurance Tests

- **`error-states.spec.ts`** - Error handling, network failures, graceful degradation
- **`accessibility.spec.ts`** - WCAG 2.1 AA compliance, keyboard navigation, screen reader support

## Test Architecture

### Page Object Model
Tests use the `AppPage` class from `utils.ts` for consistent interaction patterns:

```typescript
import { test, AppPage } from './utils';

test('example test', async ({ page }) => {
  const appPage = new AppPage(page);
  await appPage.navigateToSynthesis();
  await appPage.synthesizeText('Hello world');
  // ... test logic
});
```

### Common Helpers
The `utils.ts` file provides:
- Navigation helpers
- Form interaction utilities  
- Audio playback testing
- Modal management
- Accessibility checking
- Mobile/responsive testing
- API mocking utilities

### Test Data
Centralized test data in `testData` object:
- Sample profile configurations
- Text synthesis examples
- SSML templates
- Common URLs

## Configuration

### `playwright.config.ts`
- Base URL: `http://localhost:5173` (dev) or `http://localhost:3100` (Docker)
- Browsers: Chrome, Firefox, Safari, Mobile Chrome/Safari
- Auto-starts dev server if not running
- Screenshots on failure
- Video recording on failure
- Trace collection for debugging

### Environment Variables
- `E2E_BASE_URL` - Override base URL for tests
- `CI` - Enables CI-specific settings (retries, workers)

## Test Patterns

### Resilient Selectors
Tests use multiple fallback selectors for robustness:

```typescript
// Multiple selector strategy
const playButton = page.locator('button').filter({ hasText: /play/i }).or(
  page.locator('[data-testid="play-btn"]')
);
```

### Graceful Degradation Testing
Tests handle optional features gracefully:

```typescript
const optionalFeature = page.locator('text=Advanced');
if (await optionalFeature.isVisible()) {
  // Test the feature if present
  await optionalFeature.click();
}
```

### Loading State Handling
All async operations wait for completion:

```typescript
await page.click('button');
await page.waitForTimeout(500); // Allow for animations
const result = page.locator('[data-testid="result"]');
await expect(result).toBeVisible({ timeout: 10000 });
```

## Best Practices

### Test Independence
- Each test is self-contained
- No dependencies between tests
- Clean state for each test

### Realistic User Interactions
- Tests mimic real user behavior
- Proper wait times for UI animations
- Keyboard and mouse interactions

### Accessibility Testing
- Screen reader compatibility
- Keyboard navigation
- ARIA compliance
- Color contrast verification

### Cross-Browser Testing
- Chrome (primary)
- Firefox
- Safari/WebKit
- Mobile browsers

### Error Scenarios
- Network failures
- API errors
- Invalid input handling
- Authentication issues

## Debugging

### Debug Mode
```bash
npm run test:e2e:debug
```

### Screenshots
Automatic screenshots on failure are saved to `test-results/`

### Video Recording
Videos of failed tests are saved to `test-results/`

### Trace Viewer
View detailed execution traces:
```bash
npx playwright show-trace trace.zip
```

### Console Output
Check browser console messages:
```typescript
// In test files
const logs = await page.evaluate(() => console.log('Debug info'));
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Install Playwright
  run: npm run test:e2e:install

- name: Run E2E tests
  run: npm run test:e2e
  
- name: Upload test results
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: playwright-report
    path: playwright-report/
```

### Docker Support
Tests can run against Dockerized application:

```bash
# Start app in Docker
make docker-up

# Run tests against Docker instance
E2E_BASE_URL=http://localhost:3100 npm run test:e2e
```

## Test Data

### Authentication
Since `AUTH_DISABLED=true` by default, tests run without authentication.

### Sample Data
Tests work with both empty state and populated data states.

### API Mocking
Complex API interactions can be mocked:

```typescript
await appPage.mockApiResponse('/api/v1/voices', mockVoicesData);
```

## Performance Testing

Tests include basic performance checks:
- Page load times
- Network request counts
- Memory usage monitoring
- Slow network simulation

## Maintenance

### Updating Selectors
When UI changes, update selectors in `utils.ts` for centralized management.

### Adding New Tests
1. Create new `.spec.ts` file in `e2e/` directory
2. Follow existing patterns
3. Use `AppPage` helper methods
4. Add to test suite documentation

### Browser Updates
Keep Playwright browsers updated:
```bash
npm run test:e2e:install
```

## Troubleshooting

### Common Issues

**Tests timing out:**
- Increase timeout values
- Check if dev server is running
- Verify network connectivity

**Element not found:**
- Check selector specificity
- Verify element is visible
- Add wait conditions

**Flaky tests:**
- Add proper wait conditions
- Use `waitForTimeout` sparingly
- Prefer `waitForSelector` over fixed delays

### Getting Help
1. Check test output in `playwright-report/`
2. Review browser console logs
3. Use trace viewer for detailed debugging
4. Check network requests in browser dev tools

## Integration with Development

### Pre-commit Hooks
Consider adding E2E tests to pre-commit hooks for critical flows.

### Development Workflow
1. Write feature
2. Run unit tests
3. Run relevant E2E tests
4. Run full E2E suite before merge

### Continuous Testing
Set up E2E tests to run on:
- Pull requests
- Nightly builds
- Production deployments