import type { TestWorkspace } from '../shared/model/workspace';
import { apiUrl } from './client';
import { bootstrapSession, parseTestWorkspace } from './workspaces';

interface SaveProductConfigurationOptions {
  testId?: string;
  productImage?: File;
  productDescription: string;
  totalQuestions: number;
}

interface ErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    field_errors?: Record<string, string[]>;
  };
}

export class QuestionConfigurationRequestError extends Error {
  constructor(
    message: string,
    readonly code = 'question_configuration_request_failed',
    readonly fieldErrors: Record<string, string[]> = {},
  ) {
    super(message);
  }
}

export async function saveProductConfiguration({
  testId,
  productImage,
  productDescription,
  totalQuestions,
}: SaveProductConfigurationOptions): Promise<TestWorkspace> {
  await bootstrapSession();
  const form = new FormData();
  if (productImage) form.append('productImage', productImage, productImage.name);
  form.append('productDescription', productDescription);
  form.append('totalQuestions', String(totalQuestions));

  let response: Response;
  try {
    response = await fetch(
      apiUrl(testId ? `/api/v1/tests/${testId}/configuration` : '/api/v1/tests'),
      {
      method: testId ? 'PUT' : 'POST',
      credentials: 'include',
      body: form,
      },
    );
  } catch {
    throw new QuestionConfigurationRequestError(
      'The question setup could not be saved. Check your connection and try again.',
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new QuestionConfigurationRequestError('UVTS received an invalid setup response.');
  }
  if (!response.ok) {
    const envelope = body as ErrorEnvelope;
    throw new QuestionConfigurationRequestError(
      envelope.error?.message ?? 'The question setup could not be saved. Try again.',
      envelope.error?.code,
      envelope.error?.field_errors ?? {},
    );
  }
  return parseTestWorkspace(body);
}
