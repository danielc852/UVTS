import type { TestWorkspace } from '../shared/model/workspace';
import { requestWorkspace, type ApiErrorDetail } from './workspace-requests';

export class QuestionTransitionError extends Error {
  constructor(
    message: string,
    readonly code = 'question_transition_failed',
  ) {
    super(message);
  }
}

async function transition(path: string): Promise<TestWorkspace> {
  return requestWorkspace({
    path,
    init: { method: 'POST' },
    messages: {
      network: 'The request could not be sent. Check your connection and try again.',
      invalidResponse: 'UVTS received an invalid response.',
      failed: 'The request could not be completed. Try again.',
    },
    createError: (message: string, detail?: ApiErrorDetail) =>
      new QuestionTransitionError(message, detail?.code),
  });
}

export function generateQuestions(testId: string): Promise<TestWorkspace> {
  return transition(`/api/v1/tests/${testId}/questions`);
}

export function confirmQuestions(testId: string): Promise<TestWorkspace> {
  return transition(`/api/v1/tests/${testId}/questions/confirm`);
}

export function startOver(testId: string): Promise<TestWorkspace> {
  return transition(`/api/v1/tests/${testId}/start-over`);
}
