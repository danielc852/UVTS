import type { TestWorkspace } from '../shared/model/workspace';
import { apiUrl } from './client';
import { bootstrapSession, parseTestWorkspace } from './workspaces';

interface ErrorEnvelope {
  error?: { code?: string; message?: string };
}

export class EvaluationRequestError extends Error {
  constructor(
    message: string,
    readonly code = 'evaluation_request_failed',
  ) {
    super(message);
  }
}

async function post(path: string): Promise<TestWorkspace> {
  await bootstrapSession();
  let response: Response;
  try {
    response = await fetch(apiUrl(path), { method: 'POST', credentials: 'include' });
  } catch {
    throw new EvaluationRequestError('The evaluation request could not be sent. Check your connection and try again.');
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new EvaluationRequestError('UVTS received an invalid evaluation response.');
  }
  if (!response.ok) {
    const envelope = body as ErrorEnvelope;
    throw new EvaluationRequestError(
      envelope.error?.message ?? 'The evaluation request could not be completed. Try again.',
      envelope.error?.code,
    );
  }
  return parseTestWorkspace(body);
}

export const startEvaluation = (testId: string) => post(`/api/v1/tests/${testId}/evaluation`);
export const retryFailedQuestions = (testId: string) =>
  post(`/api/v1/tests/${testId}/evaluation/retry-failed`);
export const retryQuestion = (testId: string, questionId: string) =>
  post(`/api/v1/tests/${testId}/evaluation/${questionId}/retry`);
export const retryReport = (testId: string) => post(`/api/v1/tests/${testId}/report/retry`);
