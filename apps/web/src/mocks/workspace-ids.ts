const mockWorkspaceIds = new Set([
  'clean',
  'manual-ready',
  'configuration-saved',
  'configuration-generating',
  'questions-ready',
  'questions-generating',
  'legacy-questions',
  'upload-ready',
  'evaluating',
  'report-generating',
  'report-ready',
  'upload-error',
  'generation-error',
  'incomplete-report',
]);

export function isMockWorkspaceId(testId: string): boolean {
  return import.meta.env.VITE_ENABLE_MOCKS !== 'false' && mockWorkspaceIds.has(testId);
}
