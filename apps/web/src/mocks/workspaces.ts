import {
  type Question,
  type QuestionSet,
  type Report,
  type TestWorkspace,
} from '../entities/workspace/model';
import { createCleanWorkspace } from '../entities/workspace/clean';

const manual = {
  id: 'manual-1',
  filename: 'sample-product-manual.pdf',
  pageCount: 12,
  status: 'ready' as const,
};

const productConfiguration = {
  version: 1,
  totalQuestions: 9,
  productDescription: 'A compact smart speaker for home music and voice controls.',
  productImage: {
    id: 'product-image-1',
    filename: 'smart-speaker.png',
    contentType: 'image/png',
    sizeBytes: 2048,
  },
};

const seeds = [
  'How do I complete the initial setup?',
  'Can I change the export format after automatic backup is enabled?',
  'What should I do if setup stops before my device appears?',
];
const repeatedQuestions: Question[] = Array.from({ length: 9 }, (_, index) => ({
  id: `q${index + 1}`,
  text: `${seeds[index % seeds.length]} (${index + 1})`,
}));

const draftQuestionSet: QuestionSet = {
  id: 'question-set-1',
  status: 'draft',
  source: 'product_context_v1',
  configurationVersion: 1,
  generatedAt: '2026-08-24T00:00:00Z',
  items: repeatedQuestions,
};
const confirmedQuestionSet: QuestionSet = {
  ...draftQuestionSet,
  status: 'confirmed',
  confirmedAt: '2026-08-24T00:01:00Z',
};
const source = { questionSetId: confirmedQuestionSet.id, manualId: manual.id };

const completeReport: Report = {
  source,
  isComplete: true,
  counts: { found: 7, partly_found: 1, not_found: 1, failed: 0 },
  results: repeatedQuestions.map((question, index) => ({
    question,
    status: index < 7 ? 'found' : index === 7 ? 'partly_found' : 'not_found',
    informationNeeded: 'The steps, conditions, and limits needed to complete the task.',
    informationFound:
      index < 8 ? 'The manual describes the main steps and the supported settings.' : undefined,
    informationMissing:
      index === 7 ? 'The manual does not explain what happens when setup is interrupted.' : undefined,
    evidence:
      index < 8
        ? [{ page: (index % 5) + 2, extract: 'Follow the setup steps and confirm the device appears.' }]
        : [],
  })),
  gaps: [
    {
      id: 'gap-1',
      title: 'Interrupted setup recovery',
      whyItMatters: 'Writers need to tell users how to recover without starting over.',
      affectedQuestionIds: ['q8', 'q9'],
      kind: 'incomplete',
    },
  ],
  recommendations: [
    {
      id: 'recommendation-1',
      priority: 'Medium',
      change: 'Add a recovery section for interrupted setup.',
      reason: 'Two questions could not find complete recovery guidance.',
      gapId: 'gap-1',
    },
  ],
  followUpQuestions: ['Can I resume setup after the device reconnects?'],
};

const baseWorkspace = createCleanWorkspace();

export const workspaceFixtures = {
  clean: baseWorkspace,
  'manual-ready': {
    ...baseWorkspace,
    id: 'manual-ready',
    status: 'ready',
    currentStage: 'evaluation',
    configuration: productConfiguration,
    questionSet: confirmedQuestionSet,
    questions: repeatedQuestions,
    manual,
  },
  'configuration-saved': {
    ...baseWorkspace,
    id: 'configuration-saved',
    configuration: productConfiguration,
  },
  'configuration-generating': {
    ...baseWorkspace,
    id: 'configuration-generating',
    status: 'generating',
    currentStage: 'questions',
    configuration: productConfiguration,
  },
  'questions-ready': {
    ...baseWorkspace,
    id: 'questions-ready',
    status: 'questions_ready',
    currentStage: 'questions',
    configuration: productConfiguration,
    questionSet: draftQuestionSet,
    questions: repeatedQuestions,
  },
  'questions-generating': {
    ...baseWorkspace,
    id: 'questions-generating',
    status: 'generating',
    currentStage: 'questions',
    configuration: productConfiguration,
    questionSet: draftQuestionSet,
    questions: repeatedQuestions,
  },
  'legacy-questions': {
    ...baseWorkspace,
    id: 'legacy-questions',
    status: 'questions_ready',
    currentStage: 'questions',
    configuration: productConfiguration,
    questionSet: {
      ...draftQuestionSet,
      id: 'legacy-question-set',
      source: 'legacy_manual_unknown',
      configurationVersion: null,
    },
    questions: repeatedQuestions,
    manual,
  },
  'upload-ready': {
    ...baseWorkspace,
    id: 'upload-ready',
    status: 'questions_confirmed',
    currentStage: 'upload',
    configuration: productConfiguration,
    questionSet: confirmedQuestionSet,
    questions: repeatedQuestions,
  },
  evaluating: {
    ...baseWorkspace,
    id: 'evaluating',
    status: 'evaluating',
    currentStage: 'evaluation',
    configuration: productConfiguration,
    questionSet: confirmedQuestionSet,
    questions: repeatedQuestions,
    manual,
    evaluationSource: source,
    evaluation: repeatedQuestions.map((question, index) => ({
      questionId: question.id,
      status: index < 4 ? 'complete' : index === 4 ? 'checking' : 'waiting',
    })),
  },
  'report-ready': {
    ...baseWorkspace,
    id: 'report-ready',
    status: 'complete',
    currentStage: 'report',
    configuration: productConfiguration,
    questionSet: confirmedQuestionSet,
    questions: repeatedQuestions,
    manual,
    evaluationSource: source,
    evaluation: repeatedQuestions.map((question) => ({ questionId: question.id, status: 'complete' })),
    report: completeReport,
  },
  'upload-error': {
    ...baseWorkspace,
    id: 'upload-error',
    status: 'questions_confirmed',
    currentStage: 'upload',
    configuration: productConfiguration,
    questionSet: confirmedQuestionSet,
    questions: repeatedQuestions,
    error: {
      code: 'manual_no_readable_text',
      stage: 'upload',
      title: 'The manual was not added',
      message: 'UVTS could not read the text in this PDF. Scanned documents are not supported yet.',
      retryable: false,
    },
  },
  'generation-error': {
    ...baseWorkspace,
    id: 'generation-error',
    status: 'failed',
    configuration: productConfiguration,
    error: {
      code: 'question_generation_failed',
      stage: 'configuration',
      title: 'Questions were not created',
      message: 'Your Product setup is saved. Try generating the questions again.',
      retryable: true,
    },
  },
  'incomplete-report': {
    ...baseWorkspace,
    id: 'incomplete-report',
    status: 'incomplete',
    currentStage: 'report',
    configuration: productConfiguration,
    questionSet: confirmedQuestionSet,
    questions: repeatedQuestions,
    manual,
    evaluationSource: source,
    evaluation: repeatedQuestions.map((question, index) => ({
      questionId: question.id,
      status: index === 8 ? 'failed' : 'complete',
      error: index === 8 ? 'The question could not be checked.' : undefined,
    })),
    report: {
      ...completeReport,
      isComplete: false,
      counts: { found: 7, partly_found: 1, not_found: 0, failed: 1 },
      results: completeReport.results.slice(0, 8).concat({
        ...completeReport.results[8],
        status: 'failed',
      }),
    },
  },
} satisfies Record<string, TestWorkspace>;

export function getWorkspaceFixture(id: string): TestWorkspace | undefined {
  const fixture = (workspaceFixtures as Record<string, TestWorkspace>)[id];
  return fixture ? structuredClone(fixture) : undefined;
}
