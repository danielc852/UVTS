import type { TestWorkspace } from '../shared/model/workspace';
import { apiClient, apiUrl } from './client';
import { bootstrapSession, parseTestWorkspace } from './workspaces';

interface UploadManualOptions {
  file: File;
  testId?: string;
  onProgress?: (percent: number) => void;
}

interface ErrorEnvelope {
  error?: { code?: string; message?: string };
}

export class DocumentRequestError extends Error {
  constructor(
    message: string,
    readonly code = 'document_request_failed',
  ) {
    super(message);
  }
}

function requestError(xhr: XMLHttpRequest): DocumentRequestError {
  try {
    const body = JSON.parse(xhr.responseText) as ErrorEnvelope;
    return new DocumentRequestError(
      body.error?.message ?? 'The manual could not be uploaded. Try again.',
      body.error?.code,
    );
  } catch {
    return new DocumentRequestError('The manual could not be uploaded. Try again.');
  }
}

export async function uploadManual({
  file,
  testId,
  onProgress,
}: UploadManualOptions): Promise<TestWorkspace> {
  await bootstrapSession();
  const method = testId ? 'PUT' : 'POST';
  const path = testId ? `/api/v1/tests/${testId}/manual` : '/api/v1/tests/manual';
  const form = new FormData();
  form.append('file', file, file.name);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, apiUrl(path));
    xhr.withCredentials = true;
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && event.total > 0) {
        onProgress?.(Math.round((event.loaded / event.total) * 100));
      }
    });
    xhr.addEventListener('load', () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(requestError(xhr));
        return;
      }
      try {
        resolve(parseTestWorkspace(JSON.parse(xhr.responseText)));
      } catch {
        reject(new DocumentRequestError('UVTS received an invalid upload response.'));
      }
    });
    xhr.addEventListener('error', () => {
      reject(new DocumentRequestError('The upload was interrupted. Check your connection and try again.'));
    });
    xhr.send(form);
  });
}

export async function deleteManual(testId: string): Promise<TestWorkspace> {
  await bootstrapSession();
  const { data, error } = await apiClient.DELETE('/api/v1/tests/{test_id}/manual', {
    params: { path: { test_id: testId } },
  });
  if (error || !data) {
    const envelope = error as ErrorEnvelope | undefined;
    throw new DocumentRequestError(
      envelope?.error?.message ?? 'The manual could not be removed. Try again.',
      envelope?.error?.code,
    );
  }
  return parseTestWorkspace(data);
}

export function manualContentUrl(testId: string): string {
  return apiUrl(`/api/v1/tests/${testId}/manual/content`);
}
