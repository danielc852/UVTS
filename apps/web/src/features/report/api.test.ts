import { describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from '../../mocks/workspaces';

vi.mock('../../entities/workspace/api', () => ({
  bootstrapSession: vi.fn().mockResolvedValue(undefined),
  parseTestWorkspace: (value: unknown) => value,
}));

describe('report requests', () => {
  it('posts a retry against the persisted test lineage', async () => {
    const workspace = getWorkspaceFixture('incomplete-report');
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(workspace), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const { retryReport } = await import('./api');

    await retryReport('test-1');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/tests\/test-1\/report\/retry$/),
      { method: 'POST', credentials: 'include' },
    );
    vi.unstubAllGlobals();
  });
});
