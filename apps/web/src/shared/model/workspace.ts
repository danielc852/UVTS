import type { components } from '../../api/generated/schema';

export type WorkflowStage = components['schemas']['WorkflowStage'];
export type CoverageStatus = components['schemas']['CoverageStatus'];
export type EvaluationStatus = components['schemas']['EvaluationStatus'];
export type ManualSummary = components['schemas']['ManualSummary'];
export type ManualUpload = components['schemas']['ManualUpload'];
export type Question = components['schemas']['Question'];
export type EvaluationItem = components['schemas']['EvaluationItem'];
export type Evidence = components['schemas']['Evidence'];
export type QuestionResult = components['schemas']['QuestionResult'];
export type Gap = components['schemas']['Gap'];
export type Recommendation = components['schemas']['Recommendation'];
export type Report = components['schemas']['Report'];
export type WorkspaceError = components['schemas']['WorkspaceError'];

type ApiTestConfiguration = components['schemas']['TestConfiguration'];
type ApiTestResponse = components['schemas']['TestResponse'];

/** UI-ready form of the API configuration after server defaults are applied. */
export type TestConfiguration = Omit<ApiTestConfiguration, 'typeCounts' | 'topics' | 'viewpoints'> & {
  typeCounts: components['schemas']['QuestionTypeCounts'];
  topics: string[];
  viewpoints: string[];
};

/**
 * The workspace is the generated response without transport metadata and with
 * nullable API fields normalized for rendering.
 */
export type TestWorkspace = Omit<
  ApiTestResponse,
  | 'configuration'
  | 'manual'
  | 'manualUpload'
  | 'report'
  | 'error'
  | 'createdAt'
  | 'updatedAt'
  | 'stateVersion'
  | 'status'
> & {
  configuration: TestConfiguration;
  manual?: ManualSummary;
  manualUpload?: ManualUpload;
  report?: Report;
  error?: WorkspaceError;
};

export const workflowStages = [
  'upload',
  'configuration',
  'questions',
  'evaluation',
  'report',
] as const satisfies readonly WorkflowStage[];

export const defaultConfiguration: TestConfiguration = {
  totalQuestions: 9,
  typeCounts: { basic: 3, crossParagraph: 3, edgeCase: 3 },
  topics: [
    'Setup and requirements',
    'Main product tasks',
    'Settings and customization',
    'Troubleshooting and recovery',
    'Limits and unusual situations',
    'Safety, privacy, and data handling',
  ],
  viewpoints: ['Beginner', 'Regular user', 'Advanced user'],
};
