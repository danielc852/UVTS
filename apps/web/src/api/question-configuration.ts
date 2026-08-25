import type { TestWorkspace } from '../shared/model/workspace';
import { requestWorkspace, type ApiErrorDetail } from './workspace-requests';

interface SaveProductConfigurationOptions {
  testId?: string;
  productImage?: File;
  productDescription: string;
  totalQuestions: number;
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
  const form = new FormData();
  if (productImage) form.append('productImage', productImage, productImage.name);
  form.append('productDescription', productDescription);
  form.append('totalQuestions', String(totalQuestions));

  return requestWorkspace({
    path: testId ? `/api/v1/tests/${testId}/configuration` : '/api/v1/tests',
    init: {
      method: testId ? 'PUT' : 'POST',
      body: form,
    },
    messages: {
      network: 'The question setup could not be saved. Check your connection and try again.',
      invalidResponse: 'UVTS received an invalid setup response.',
      failed: 'The question setup could not be saved. Try again.',
    },
    createError: (message: string, detail?: ApiErrorDetail) =>
      new QuestionConfigurationRequestError(
        message,
        detail?.code,
        detail?.field_errors ?? {},
      ),
  });
}
