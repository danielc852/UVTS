import { describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from '../../mocks/workspaces';

vi.mock('../../entities/workspace/api', () => ({
  bootstrapSession: vi.fn().mockResolvedValue(undefined),
  parseTestWorkspace: (value: unknown) => value,
}));

describe('question transitions', () => {
  it.each([
    ['generateQuestions', '/api/v1/tests/test-1/questions'],
    ['confirmQuestions', '/api/v1/tests/test-1/questions/confirm'],
    ['startOver', '/api/v1/tests/test-1/start-over'],
  ] as const)('posts %s without client-owned configuration', async (method, path) => {
    const workspace = getWorkspaceFixture('questions-ready');
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(workspace), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const api = await import('./api');

    await api[method]('test-1');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(new RegExp(`${path}$`)),
      { method: 'POST', credentials: 'include' },
    );
    expect((fetchMock.mock.calls[0][1] as RequestInit).body).toBeUndefined();
    vi.unstubAllGlobals();
  });
});
