import type { TestWorkspace } from '../../entities/workspace/model';
import type { components } from '../../shared/api/generated/schema';
import { bootstrapSession } from '../../entities/workspace/api';
import { apiUrl } from '../../shared/api/client';
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

interface QuestionSuggestionResponse {
  text: string;
}

export async function suggestQuestion(
  testId: string,
  direction: string,
  existingQuestions: string[],
): Promise<string> {
  await bootstrapSession();
  let response: Response;
  try {
    response = await fetch(apiUrl(`/api/v1/tests/${testId}/questions/suggestion`), {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ direction, existingQuestions }),
    });
  } catch {
    throw new QuestionTransitionError(
      'The request could not be sent. Check your connection and try again.',
    );
  }

  let body: QuestionSuggestionResponse | { error?: ApiErrorDetail };
  try {
    body = await response.json();
  } catch {
    throw new QuestionTransitionError('UVTS received an invalid response.');
  }
  if (!response.ok) {
    const detail = 'error' in body ? body.error : undefined;
    throw new QuestionTransitionError(
      detail?.message ?? 'The question could not be generated. Try again.',
      detail?.code,
      detail?.field_errors,
    );
  }
  if (!('text' in body) || typeof body.text !== 'string' || !body.text.trim()) {
    throw new QuestionTransitionError('UVTS received an invalid question. Try again.');
  }
  return body.text.trim();
}
