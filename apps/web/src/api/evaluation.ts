import type { TestWorkspace } from '../shared/model/workspace';
import { requestWorkspace, type ApiErrorDetail } from './workspace-requests';

export class EvaluationRequestError extends Error {
  constructor(
    message: string,
    readonly code = 'evaluation_request_failed',
  ) {
    super(message);
  }
}

async function post(path: string): Promise<TestWorkspace> {
  return requestWorkspace({
    path,
    init: { method: 'POST' },
    messages: {
      network: 'The evaluation request could not be sent. Check your connection and try again.',
      invalidResponse: 'UVTS received an invalid evaluation response.',
      failed: 'The evaluation request could not be completed. Try again.',
    },
    createError: (message: string, detail?: ApiErrorDetail) =>
      new EvaluationRequestError(message, detail?.code),
  });
}

export function startEvaluation(testId: string): Promise<TestWorkspace> {
  return post(`/api/v1/tests/${testId}/evaluation`);
}

export function retryFailedQuestions(testId: string): Promise<TestWorkspace> {
  return post(`/api/v1/tests/${testId}/evaluation/retry-failed`);
}

export function retryQuestion(testId: string, questionId: string): Promise<TestWorkspace> {
  return post(`/api/v1/tests/${testId}/evaluation/${questionId}/retry`);
}

export function retryReport(testId: string): Promise<TestWorkspace> {
  return post(`/api/v1/tests/${testId}/report/retry`);
}
