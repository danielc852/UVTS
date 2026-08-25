import { expect, test } from '@playwright/test';

const samplePdf = Buffer.from(
  'JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovUHJvZHVjZXIgKHB5cGRmKQo+PgplbmRvYmoKMiAwIG9iago8PAovVHlwZSAvUGFnZXMKL0NvdW50IDMKL0tpZHMgWyA0IDAgUiA3IDAgUiAxMCAwIFIgXQo+PgplbmRvYmoKMyAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1Jlc291cmNlcyA8PAovRm9udCA8PAovRjEgNSAwIFIKPj4KPj4KL01lZGlhQm94IFsgMC4wIDAuMCA2MTIgNzkyIF0KL1BhcmVudCAyIDAgUgovQ29udGVudHMgNiAwIFIKPj4KZW5kb2JqCjUgMCBvYmoKPDwKL1R5cGUgL0ZvbnQKL1N1YnR5cGUgL1R5cGUxCi9CYXNlRm9udCAvSGVsdmV0aWNhCj4+CmVuZG9iago2IDAgb2JqCjw8Ci9MZW5ndGggNDYKPj4Kc3RyZWFtCkJUIC9GMSAxMiBUZiA3MiA3MjAgVGQgKFJlYWRhYmxlIHBhZ2UgMSkgVGogRVQKZW5kc3RyZWFtCmVuZG9iago3IDAgb2JqCjw8Ci9UeXBlIC9QYWdlCi9SZXNvdXJjZXMgPDwKL0ZvbnQgPDwKL0YxIDggMCBSCj4+Cj4+Ci9NZWRpYUJveCBbIDAuMCAwLjAgNjEyIDc5MiBdCi9QYXJlbnQgMiAwIFIKL0NvbnRlbnRzIDkgMCBSCj4+CmVuZG9iago4IDAgb2JqCjw8Ci9UeXBlIC9Gb250Ci9TdWJ0eXBlIC9UeXBlMQovQmFzZUZvbnQgL0hlbHZldGljYQo+PgplbmRvYmoKOSAwIG9iago8PAovTGVuZ3RoIDQ2Cj4+CnN0cmVhbQpCVCAvRjEgMTIgVGYgNzIgNzIwIFRkIChSZWFkYWJsZSBwYWdlIDIpIFRqIEVUCmVuZHN0cmVhbQplbmRvYmoKMTAgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1Jlc291cmNlcyA8PAovRm9udCA8PAovRjEgMTEgMCBSCj4+Cj4+Ci9NZWRpYUJveCBbIDAuMCAwLjAgNjEyIDc5MiBdCi9QYXJlbnQgMiAwIFIKL0NvbnRlbnRzIDEyIDAgUgo+PgplbmRvYmoKMTEgMCBvYmoKPDwKL1R5cGUgL0ZvbnQKL1N1YnR5cGUgL1R5cGUxCi9CYXNlRm9udCAvSGVsdmV0aWNhCj4+CmVuZG9iagoxMiAwIG9iago8PAovTGVuZ3RoIDQ2Cj4+CnN0cmVhbQpCVCAvRjEgMTIgVGYgNzIgNzIwIFRkIChSZWFkYWJsZSBwYWdlIDMpIFRqIEVUCmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDEzCjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAxNSAwMDAwMCBuIAowMDAwMDAwMDU0IDAwMDAwIG4gCjAwMDAwMDAxMjYgMDAwMDAgbiAKMDAwMDAwMDE3NSAwMDAwMCBuIAowMDAwMDAwMzA3IDAwMDAwIG4gCjAwMDAwMDAzNzcgMDAwMDAgbiAKMDAwMDAwMDQ3MyAwMDAwMCBuIAowMDAwMDAwNjA1IDAwMDAwIG4gCjAwMDAwMDA2NzUgMDAwMDAgbiAKMDAwMDAwMDc3MSAwMDAwMCBuIAowMDAwMDAwOTA2IDAwMDAwIG4gCjAwMDAwMDA5NzcgMDAwMDAgbiAKdHJhaWxlcgo8PAovU2l6ZSAxMwovUm9vdCAzIDAgUgovSW5mbyAxIDAgUgo+PgpzdGFydHhyZWYKMTA3NAolJUVPRgo=',
  'base64',
);

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
  await expect(page.getByRole('heading', { name: '1. Product setup' })).toBeVisible();
});

test('restores a completed test from its route', async ({ page }) => {
  await page.goto('/tests/report-ready');
  await expect(page.getByText('7 questions are covered out of 9 total questions.')).toBeVisible();
  await expect(page.getByText('Information partly found').first()).toBeVisible();
});

test('moves back through completed steps and forward to the current step', async ({ page }) => {
  await page.goto('/tests/report-ready');
  await page.getByRole('button', { name: 'Back to Evaluation' }).click();
  await expect(page.getByRole('heading', { name: '4. Evaluation' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '5. Report' })).not.toBeVisible();
  await page.getByRole('button', { name: 'Continue to Report' }).click();
  await expect(page.getByRole('heading', { name: '5. Report' })).toBeVisible();
});

test('reflows without horizontal page scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('/tests/report-ready');
  await expect(page.getByRole('heading', { name: '5. Report' })).toBeVisible();
  const widths = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(widths.content).toBeLessThanOrEqual(widths.viewport);
});

test('keeps the question editor in a scrollable region', async ({ page }) => {
  await page.goto('/tests/questions-ready');

  const questionList = page.getByRole('region', { name: 'Editable question list' });
  await expect(questionList).toBeVisible();

  const layout = await questionList.evaluate((element) => {
    const listBounds = element.getBoundingClientRect();
    const actions = document.querySelector('.question-editor-actions');
    const actionBounds = actions?.getBoundingClientRect();

    return {
      clientHeight: element.clientHeight,
      scrollHeight: element.scrollHeight,
      overflowY: getComputedStyle(element).overflowY,
      listBottom: listBounds.bottom,
      actionsTop: actionBounds?.top,
    };
  });

  expect(layout.overflowY).toBe('auto');
  expect(layout.scrollHeight).toBeGreaterThan(layout.clientHeight);
  expect(layout.actionsTop).toBeGreaterThanOrEqual(layout.listBottom);
});

test('renders and keyboard-scrolls the uploaded PDF without page overflow', async ({ page }) => {
  let pdfRequests = 0;
  await page.route('**/api/v1/tests/manual-ready/manual/content', (route) => {
    pdfRequests += 1;
    return route.fulfill({
      status: 200,
      contentType: 'application/pdf',
      headers: { 'accept-ranges': 'bytes', 'cache-control': 'private, no-store' },
      body: samplePdf,
    });
  });
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('/tests/manual-ready');
  expect(pdfRequests).toBe(0);
  await page
    .getByRole('navigation', { name: 'Test progress' })
    .getByRole('button', { name: /^Upload/ })
    .click();

  const viewer = page.getByRole('region', { name: /document preview/ });
  await expect(viewer).toBeVisible();
  await expect.poll(() => pdfRequests).toBeGreaterThan(0);
  await expect(viewer.getByText('Page 1 of 3')).toBeVisible();
  await expect.poll(() => viewer.locator('canvas').first().evaluate((canvas) => canvas.width)).toBeGreaterThan(0);
  const before = await viewer.evaluate((element) => ({
    scrollHeight: element.scrollHeight,
    clientHeight: element.clientHeight,
    scrollTop: element.scrollTop,
  }));
  expect(before.scrollHeight).toBeGreaterThan(before.clientHeight);
  await viewer.focus();
  await page.keyboard.press('PageDown');
  await expect.poll(() => viewer.evaluate((element) => element.scrollTop)).toBeGreaterThan(0);
  const widths = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(widths.content).toBeLessThanOrEqual(widths.viewport);
});
