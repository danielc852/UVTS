import {
  defaultConfiguration,
  type Question,
  type Report,
  type TestWorkspace,
} from '../../shared/model/workspace';

const manual = {
  id: 'manual-1',
  filename: 'sample-product-manual.pdf',
  pageCount: 12,
  status: 'ready' as const,
};

const questions: Question[] = [
  {
    id: 'q1',
    text: 'How do I complete the initial setup?',
    type: 'Basic',
    topic: 'Setup and requirements',
    viewpoint: 'Beginner',
  },
  {
    id: 'q2',
    text: 'Can I change the export format after automatic backup is enabled?',
    type: 'Cross-paragraph',
    topic: 'Settings and customization',
    viewpoint: 'Regular user',
  },
  {
    id: 'q3',
    text: 'What should I do if setup stops before my device appears?',
    type: 'Edge-case',
    topic: 'Troubleshooting and recovery',
    viewpoint: 'Advanced user',
  },
];

const repeatedQuestions = Array.from({ length: 9 }, (_, index) => {
  const source = questions[index % questions.length];
  return { ...source, id: `q${index + 1}`, text: `${source.text} (${index + 1})` };
});

const completeReport: Report = {
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

const baseWorkspace: TestWorkspace = {
  id: 'clean',
  currentStage: 'upload',
  configuration: defaultConfiguration,
  questions: [],
  evaluation: [],
};

export const workspaceFixtures = {
  clean: baseWorkspace,
  'manual-ready': {
    ...baseWorkspace,
    id: 'manual-ready',
    currentStage: 'configuration',
    manual,
  },
  'questions-ready': {
    ...baseWorkspace,
    id: 'questions-ready',
    currentStage: 'questions',
    manual,
    questions: repeatedQuestions,
  },
  evaluating: {
    ...baseWorkspace,
    id: 'evaluating',
    currentStage: 'evaluation',
    manual,
    questions: repeatedQuestions,
    evaluation: repeatedQuestions.map((question, index) => ({
      questionId: question.id,
      status: index < 4 ? 'complete' : index === 4 ? 'checking' : 'waiting',
    })),
  },
  'report-ready': {
    ...baseWorkspace,
    id: 'report-ready',
    currentStage: 'report',
    manual,
    questions: repeatedQuestions,
    evaluation: repeatedQuestions.map((question) => ({ questionId: question.id, status: 'complete' })),
    report: completeReport,
  },
  'upload-error': {
    ...baseWorkspace,
    id: 'upload-error',
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
    currentStage: 'configuration',
    manual,
    error: {
      code: 'generation_failed',
      stage: 'configuration',
      title: 'Questions were not created',
      message: 'Your manual and settings are still here. Try generating the questions again.',
      retryable: true,
    },
  },
  'incomplete-report': {
    ...baseWorkspace,
    id: 'incomplete-report',
    currentStage: 'report',
    manual,
    questions: repeatedQuestions,
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
