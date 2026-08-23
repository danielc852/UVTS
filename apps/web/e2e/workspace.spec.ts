import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/session', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ authenticated: true, expires_in_seconds: 86_400 }),
    }),
  );
});

test('shows only the current stage in the clean workspace', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Check a manual' })).toBeVisible();
  await expect(page.getByRole('heading', { level: 2 })).toHaveCount(1);
  await expect(page.getByRole('heading', { name: '1. Upload manual' })).toBeVisible();
});

test('restores a completed test from its route', async ({ page }) => {
  await page.goto('/tests/report-ready');
  await expect(page.getByText('7 questions are covered out of 9 total questions.')).toBeVisible();
  await expect(page.getByText('Information partly found').first()).toBeVisible();
});

test('moves back through completed steps and forward to the current step', async ({ page }) => {
  await page.goto('/tests/report-ready');
  await page.getByRole('button', { name: 'Back to Evaluate' }).click();
  await expect(page.getByRole('heading', { name: '4. Evaluation' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '5. Report' })).not.toBeVisible();
  await page.getByRole('button', { name: 'Continue to Report' }).click();
  await expect(page.getByRole('heading', { name: '5. Report' })).toBeVisible();
});

test('reflows without horizontal page scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('/tests/report-ready');
  await expect(page.getByRole('heading', { name: 'Report' })).toBeVisible();
  const widths = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(widths.content).toBeLessThanOrEqual(widths.viewport);
});
