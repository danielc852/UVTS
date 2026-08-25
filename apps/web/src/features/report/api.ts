import type { TestWorkspace } from '../../entities/workspace/model';
import { requestWorkspace, type ApiErrorDetail } from '../../shared/api/workspace-requests';

export class ReportRequestError extends Error {
  constructor(
    message: string,
    readonly code = 'report_request_failed',
  ) {
    super(message);
  }
}

export function retryReport(testId: string): Promise<TestWorkspace> {
  return requestWorkspace({
    path: `/api/v1/tests/${testId}/report/retry`,
    init: { method: 'POST' },
    messages: {
      network: 'The report retry could not be sent. Check your connection and try again.',
      invalidResponse: 'UVTS received an invalid report response.',
      failed: 'The report retry could not be started. Try again.',
    },
    createError: (message: string, detail?: ApiErrorDetail) =>
      new ReportRequestError(message, detail?.code),
  });
}
