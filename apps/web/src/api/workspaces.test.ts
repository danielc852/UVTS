import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { server } from '../test/server';

describe('bootstrapSession', () => {
  it('bootstraps the API session once even when fixture mode is enabled', async () => {
    vi.resetModules();
    let requestCount = 0;
    server.use(
      http.post('*/api/v1/session', () => {
        requestCount += 1;
        return HttpResponse.json({ authenticated: true, expires_in_seconds: 86_400 });
      }),
    );
    const { bootstrapSession } = await import('./workspaces');

    await Promise.all([bootstrapSession(), bootstrapSession()]);

    expect(requestCount).toBe(1);
  });
});
