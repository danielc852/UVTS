import { describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from './fixtures/workspaces';

vi.mock('./workspaces', () => ({
  bootstrapSession: vi.fn().mockResolvedValue(undefined),
  parseTestWorkspace: (value: unknown) => value,
}));

describe('question configuration requests', () => {
  it('creates a test from Product setup before a manual exists', async () => {
    const workspace = getWorkspaceFixture('configuration-saved');
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(workspace), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const { saveProductConfiguration } = await import('./question-configuration');

    await saveProductConfiguration({
      productImage: new File(['image'], 'speaker.png', { type: 'image/png' }),
      productDescription: 'A compact smart speaker.',
      totalQuestions: 5,
    });

    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v1\/tests$/);
    expect(request.method).toBe('POST');
    vi.unstubAllGlobals();
  });

  it('sends the product context as credentialed multipart data', async () => {
    const workspace = getWorkspaceFixture('configuration-saved');
    expect(workspace).toBeDefined();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(workspace), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const { saveProductConfiguration } = await import('./question-configuration');
    const image = new File(['image'], 'speaker.png', { type: 'image/png' });

    await saveProductConfiguration({
      testId: 'test-1',
      productImage: image,
      productDescription: 'A compact smart speaker.',
      totalQuestions: 9,
    });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v1\/tests\/test-1\/configuration$/);
    expect(request.method).toBe('PUT');
    expect(request.credentials).toBe('include');
    const body = request.body as FormData;
    const savedImage = body.get('productImage');
    expect(savedImage).toBeInstanceOf(File);
    expect((savedImage as File).name).toBe('speaker.png');
    expect((savedImage as File).type).toBe('image/png');
    expect(body.get('productDescription')).toBe('A compact smart speaker.');
    expect(body.get('totalQuestions')).toBe('9');
    vi.unstubAllGlobals();
  });

  it('preserves server field errors for inline form feedback', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: 'product_image_required',
              message: 'Add a product image before saving the question setup.',
              field_errors: {
                productImage: ['Add a product image before saving the question setup.'],
              },
            },
          }),
          { status: 422, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );
    const { saveProductConfiguration } = await import('./question-configuration');

    await expect(
      saveProductConfiguration({
        testId: 'test-1',
        productDescription: 'A product description.',
        totalQuestions: 9,
      }),
    ).rejects.toMatchObject({
      code: 'product_image_required',
      fieldErrors: {
        productImage: ['Add a product image before saving the question setup.'],
      },
    });
    vi.unstubAllGlobals();
  });

  it('falls back safely when an error response has no field-error map', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Not Found' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    const { saveProductConfiguration } = await import('./question-configuration');

    await expect(
      saveProductConfiguration({
        testId: 'test-1',
        productDescription: 'A product description.',
        totalQuestions: 9,
      }),
    ).rejects.toMatchObject({
      message: 'The question setup could not be saved. Try again.',
      fieldErrors: {},
    });
    vi.unstubAllGlobals();
  });
});
