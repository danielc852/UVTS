import type { TestWorkspace } from '../shared/model/workspace';
import { apiUrl } from './client';
import { bootstrapSession, parseTestWorkspace } from './workspaces';

interface ErrorEnvelope {
  error?: { code?: string; message?: string };
}

export class QuestionTransitionError extends Error {
  constructor(
    message: string,
    readonly code = 'question_transition_failed',
  ) {
    super(message);
  }
}

async function transition(path: string): Promise<TestWorkspace> {
  await bootstrapSession();
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    throw new QuestionTransitionError('The request could not be sent. Check your connection and try again.');
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new QuestionTransitionError('UVTS received an invalid response.');
  }
  if (!response.ok) {
    const envelope = body as ErrorEnvelope;
    throw new QuestionTransitionError(
      envelope.error?.message ?? 'The request could not be completed. Try again.',
      envelope.error?.code,
    );
  }
  return parseTestWorkspace(body);
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
