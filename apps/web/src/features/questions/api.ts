import type { TestWorkspace } from '../../entities/workspace/model';
import type { components } from '../../shared/api/generated/schema';
import { requestWorkspace, type ApiErrorDetail } from '../../shared/api/workspace-requests';

export class QuestionTransitionError extends Error {
  constructor(
    message: string,
    readonly code = 'question_transition_failed',
    readonly fieldErrors?: Record<string, string[]>,
  ) {
    super(message);
  }
}

async function transition(path: string, body?: unknown): Promise<TestWorkspace> {
  return requestWorkspace({
    path,
    init: {
      method: 'POST',
      ...(body === undefined
        ? {}
        : {
            body: JSON.stringify(body),
            headers: { 'Content-Type': 'application/json' },
          }),
    },
    messages: {
      network: 'The request could not be sent. Check your connection and try again.',
      invalidResponse: 'UVTS received an invalid response.',
      failed: 'The request could not be completed. Try again.',
    },
    createError: (message: string, detail?: ApiErrorDetail) =>
      new QuestionTransitionError(message, detail?.code, detail?.field_errors),
  });
}

export function generateQuestions(testId: string): Promise<TestWorkspace> {
  return transition(`/api/v1/tests/${testId}/questions`);
}

export type ConfirmQuestionItem = components['schemas']['ConfirmQuestionItem'];

export function confirmQuestions(
  testId: string,
  items: ConfirmQuestionItem[],
): Promise<TestWorkspace> {
  return transition(`/api/v1/tests/${testId}/questions/confirm`, { items });
}

export function startOver(testId: string): Promise<TestWorkspace> {
  return transition(`/api/v1/tests/${testId}/start-over`);
}
