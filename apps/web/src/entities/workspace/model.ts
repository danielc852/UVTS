import type { components } from '../../shared/api/generated/schema';

export type WorkflowStage = components['schemas']['WorkflowStage'];
export type TestStatus = components['schemas']['TestStatus'];
export type CoverageStatus = components['schemas']['CoverageStatus'];
export type EvaluationStatus = components['schemas']['EvaluationStatus'];
export type ManualSummary = components['schemas']['ManualSummary'];
export type ManualUpload = components['schemas']['ManualUpload'];
export type ProductImageSummary = components['schemas']['ProductImageSummary'];
export type Question = components['schemas']['Question'];
export type QuestionSet = components['schemas']['QuestionSet'];
export type EvaluationSource = components['schemas']['EvaluationSource'];
export type EvaluationItem = components['schemas']['EvaluationItem'];
export type Evidence = components['schemas']['Evidence'];
export type QuestionResult = components['schemas']['QuestionResult'];
export type Gap = components['schemas']['Gap'];
export type Recommendation = components['schemas']['Recommendation'];
export type Report = components['schemas']['Report'];
export type WorkspaceError = components['schemas']['WorkspaceError'];

type ApiTestConfiguration = components['schemas']['TestConfiguration'];
type ApiTestResponse = components['schemas']['TestResponse'];

export type TestConfiguration = Omit<
  ApiTestConfiguration,
  'productImage' | 'productDescription' | 'version' | 'totalQuestions'
> & {
  version: number;
  totalQuestions: number;
  productImage?: ProductImageSummary;
  productDescription: string;
};

export type TestWorkspace = Omit<
  ApiTestResponse,
  | 'configuration'
  | 'manual'
  | 'manualUpload'
  | 'questionSet'
  | 'evaluationSource'
  | 'evaluation'
  | 'report'
  | 'error'
  | 'createdAt'
  | 'updatedAt'
  | 'stateVersion'
  | 'schemaVersion'
> & {
  schemaVersion: number;
  configuration: TestConfiguration;
  manual?: ManualSummary;
  manualUpload?: ManualUpload;
  questionSet?: QuestionSet;
  questions: Question[];
  evaluationSource?: EvaluationSource;
  evaluation: EvaluationItem[];
  report?: Report;
  error?: WorkspaceError;
};

export const workflowStages = [
  'configuration',
  'questions',
  'upload',
  'evaluation',
  'report',
] as const satisfies readonly WorkflowStage[];

export const defaultConfiguration: TestConfiguration = {
  version: 0,
  totalQuestions: 9,
  productDescription: '',
};
