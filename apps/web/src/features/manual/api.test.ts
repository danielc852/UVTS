import { describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from '../../mocks/workspaces';

vi.mock('../../entities/workspace/api', () => ({
  bootstrapSession: vi.fn().mockResolvedValue(undefined),
  parseTestWorkspace: (value: unknown) => value,
}));

class TestXMLHttpRequest extends EventTarget {
  static responseStatus = 202;
  static responseBody = '{}';
  static latest: TestXMLHttpRequest | undefined;

  method = '';
  url = '';
  status = 0;
  responseText = '';
  upload = new EventTarget();
  withCredentials = false;

  constructor() {
    super();
    TestXMLHttpRequest.latest = this;
  }

  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }

  send(body: Document | XMLHttpRequestBodyInit | null) {
    expect(body).toBeInstanceOf(FormData);
    this.upload.dispatchEvent(
      new ProgressEvent('progress', { lengthComputable: true, loaded: 5, total: 10 }),
    );
    this.status = TestXMLHttpRequest.responseStatus;
    this.responseText = TestXMLHttpRequest.responseBody;
    this.dispatchEvent(new Event('load'));
  }
}

describe('document requests', () => {
  it('uses a credentialed XHR and reports multipart upload progress', async () => {
    const workspace = getWorkspaceFixture('manual-ready');
    expect(workspace).toBeDefined();
    TestXMLHttpRequest.responseStatus = 202;
    TestXMLHttpRequest.responseBody = JSON.stringify(workspace);
    vi.stubGlobal('XMLHttpRequest', TestXMLHttpRequest);
    const { uploadManual } = await import('./api');
    const progress = vi.fn();

    const result = await uploadManual({
      file: new File(['%PDF-test'], 'manual.pdf', { type: 'application/pdf' }),
      testId: 'test-1',
      onProgress: progress,
    });

    expect(result).toEqual(workspace);
    expect(progress).toHaveBeenCalledWith(50);
    expect(TestXMLHttpRequest.latest?.method).toBe('PUT');
    expect(TestXMLHttpRequest.latest?.url).toMatch(/\/api\/v1\/tests\/test-1\/manual$/);
    expect(TestXMLHttpRequest.latest?.withCredentials).toBe(true);
    vi.unstubAllGlobals();
  });

  it('preserves the approved server error copy and machine-readable code', async () => {
    TestXMLHttpRequest.responseStatus = 422;
    TestXMLHttpRequest.responseBody = JSON.stringify({
      error: {
        code: 'manual_password_protected',
        message: 'This PDF is password-protected. Remove the password and upload it again.',
      },
    });
    vi.stubGlobal('XMLHttpRequest', TestXMLHttpRequest);
    const { uploadManual } = await import('./api');

    const request = uploadManual({
      file: new File(['%PDF-test'], 'locked.pdf', { type: 'application/pdf' }),
      testId: 'test-1',
    });

    await expect(request).rejects.toMatchObject({
      name: 'Error',
      code: 'manual_password_protected',
      message: 'This PDF is password-protected. Remove the password and upload it again.',
    });
    expect(TestXMLHttpRequest.latest?.method).toBe('PUT');
    vi.unstubAllGlobals();
  });
});
