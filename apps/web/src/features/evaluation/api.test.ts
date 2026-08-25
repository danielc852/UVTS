import { describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from '../../mocks/workspaces';

vi.mock('../../entities/workspace/api', () => ({
  bootstrapSession: vi.fn().mockResolvedValue(undefined),
  parseTestWorkspace: (value: unknown) => value,
}));

describe('evaluation requests', () => {
  it.each([
    ['startEvaluation', ['test-1'], '/api/v1/tests/test-1/evaluation'],
    ['retryFailedQuestions', ['test-1'], '/api/v1/tests/test-1/evaluation/retry-failed'],
    ['retryQuestion', ['test-1', 'question-1'], '/api/v1/tests/test-1/evaluation/question-1/retry'],
  ] as const)('posts %s to the persisted test lineage', async (method, arguments_, path) => {
    const workspace = getWorkspaceFixture('evaluating');
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(workspace), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const api = await import('./api');

    const operation = api[method] as (...arguments__: string[]) => Promise<unknown>;
    await operation(...arguments_);

    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(new RegExp(`${path}$`)), {
      method: 'POST',
      credentials: 'include',
    });
    expect((fetchMock.mock.calls[0][1] as RequestInit).body).toBeUndefined();
    vi.unstubAllGlobals();
  });

  it('preserves a transition error code and plain-language message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: 'evaluation_not_ready',
              message: 'Confirm questions and attach a ready manual before evaluation.',
            },
          }),
          { status: 409, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );
    const { startEvaluation } = await import('./api');

    await expect(startEvaluation('test-1')).rejects.toMatchObject({
      code: 'evaluation_not_ready',
      message: 'Confirm questions and attach a ready manual before evaluation.',
    });
    vi.unstubAllGlobals();
  });
});
