import { describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from '../../mocks/workspaces';

vi.mock('../../entities/workspace/api', () => ({
  bootstrapSession: vi.fn().mockResolvedValue(undefined),
  parseTestWorkspace: (value: unknown) => value,
}));

describe('question transitions', () => {
  it.each([
    ['generateQuestions', '/api/v1/tests/test-1/questions'],
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

  it('posts the reviewed question items when confirming', async () => {
    const workspace = getWorkspaceFixture('questions-ready');
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(workspace), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const api = await import('./api');

    await api.confirmQuestions('test-1', [
      { id: 'q1', text: 'Edited question' },
      { text: 'New question' },
    ]);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/tests\/test-1\/questions\/confirm$/),
      {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: [
            { id: 'q1', text: 'Edited question' },
            { text: 'New question' },
          ],
        }),
      },
    );
    vi.unstubAllGlobals();
  });

  it('preserves field validation details from a failed confirmation', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: 'question_review_invalid',
            message: 'Questions must be unique.',
            field_errors: { 'items.1.text': ['Enter a unique question.'] },
          },
        }),
        { status: 422, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);
    const api = await import('./api');

    await expect(api.confirmQuestions('test-1', [{ text: 'Duplicate' }])).rejects.toMatchObject({
      code: 'question_review_invalid',
      fieldErrors: { 'items.1.text': ['Enter a unique question.'] },
    });
    vi.unstubAllGlobals();
  });
});
