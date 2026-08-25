import type { TestWorkspace } from '../shared/model/workspace';
import { apiUrl } from './client';
import { bootstrapSession, parseTestWorkspace } from './workspaces';

export interface ApiErrorDetail {
  code?: string;
  message?: string;
  field_errors?: Record<string, string[]>;
}

export interface ApiErrorEnvelope {
  error?: ApiErrorDetail;
}

interface RequestMessages {
  network: string;
  invalidResponse: string;
  failed: string;
}

interface WorkspaceRequestOptions<RequestError extends Error> {
  path: string;
  init: RequestInit;
  messages: RequestMessages;
  createError: (message: string, detail?: ApiErrorDetail) => RequestError;
}

export async function requestWorkspace<RequestError extends Error>({
  path,
  init,
  messages,
  createError,
}: WorkspaceRequestOptions<RequestError>): Promise<TestWorkspace> {
  await bootstrapSession();

  let response: Response;
  try {
    response = await fetch(apiUrl(path), { ...init, credentials: 'include' });
  } catch {
    throw createError(messages.network);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw createError(messages.invalidResponse);
  }

  if (!response.ok) {
    const detail = (body as ApiErrorEnvelope).error;
    throw createError(detail?.message ?? messages.failed, detail);
  }

  return parseTestWorkspace(body);
}
