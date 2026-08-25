import { z } from 'zod';

import type { TestWorkspace } from './model';

const questionSchema = z.object({ id: z.string(), text: z.string() });
const sourceSchema = z.object({ questionSetId: z.string(), manualId: z.string() });
const nullable = <T extends z.ZodTypeAny>(schema: T) =>
  schema.nullish().transform((value) => value ?? undefined);

const evaluationItemSchema = z.object({
  questionId: z.string(),
  status: z.enum(['waiting', 'checking', 'complete', 'failed']),
  error: nullable(z.string()),
});

const resultSchema = z.object({
  question: questionSchema,
  status: z.enum(['found', 'partly_found', 'not_found', 'failed']),
  informationNeeded: z.string(),
  informationFound: nullable(z.string()),
  informationMissing: nullable(z.string()),
  evidence: z.array(z.object({ page: z.number().int().positive(), extract: z.string() })).default([]),
});

const questionSetSchema = z.object({
  id: z.string(),
  status: z.enum(['draft', 'confirmed']),
  source: z.enum(['product_context_v1', 'legacy_manual_unknown']),
  configurationVersion: nullable(z.number().int().nonnegative()),
  generatedAt: nullable(z.string()),
  confirmedAt: nullable(z.string()),
  items: z.array(questionSchema).min(1).max(15),
});

const reportSchema = z.object({
  source: nullable(sourceSchema),
  isComplete: z.boolean(),
  counts: z.object({
    found: z.number().int().nonnegative(),
    partly_found: z.number().int().nonnegative(),
    not_found: z.number().int().nonnegative(),
    failed: z.number().int().nonnegative(),
  }),
  results: z.array(resultSchema),
  gaps: z.array(
    z.object({
      id: z.string(),
      title: z.string(),
      whyItMatters: z.string(),
      affectedQuestionIds: z.array(z.string()),
      kind: z.enum(['missing', 'incomplete']),
    }),
  ),
  recommendations: z.array(
    z.object({
      id: z.string(),
      priority: z.enum(['High', 'Medium', 'Low']),
      change: z.string(),
      reason: z.string(),
      gapId: z.string(),
    }),
  ),
  followUpQuestions: z.array(z.string()),
});

const apiWorkspaceSchema = z.object({
  id: z.string(),
  schemaVersion: z.number().int().min(2).default(2),
  status: z.enum([
    'draft',
    'generating',
    'questions_ready',
    'questions_confirmed',
    'ready',
    'evaluating',
    'complete',
    'incomplete',
    'failed',
  ]),
  currentStage: z.enum(['configuration', 'questions', 'upload', 'evaluation', 'report']),
  manual: nullable(
    z.object({
      id: z.string(),
      filename: z.string(),
      pageCount: z.number().int().positive(),
      status: z.enum(['checking', 'ready', 'invalid']),
    }),
  ),
  manualUpload: nullable(
    z.object({
      id: z.string(),
      filename: z.string(),
      status: z.enum(['checking', 'processing']),
    }),
  ),
  configuration: z
    .object({
      version: z.number().int().nonnegative().default(0),
      totalQuestions: z.number().int().min(1).max(15).default(9),
      productImage: nullable(
        z.object({
          id: z.string(),
          filename: z.string(),
          contentType: z.string(),
          sizeBytes: z.number().int().nonnegative(),
        }),
      ),
      productDescription: z.string().default(''),
    })
    .default({ version: 0, totalQuestions: 9, productImage: undefined, productDescription: '' }),
  questionSet: nullable(questionSetSchema),
  evaluationSource: nullable(sourceSchema),
  evaluation: z.array(evaluationItemSchema).default([]),
  report: nullable(reportSchema),
  error: nullable(
    z.object({
      code: z.string().default('workflow_error'),
      title: z.string(),
      message: z.string(),
      stage: z.enum(['configuration', 'questions', 'upload', 'evaluation', 'report']),
      retryable: z.boolean().default(false),
    }),
  ),
});

export const workspaceStateSchema: z.ZodType<TestWorkspace> = apiWorkspaceSchema.transform(
  (workspace) => ({
    ...workspace,
    questions: workspace.questionSet?.items ?? [],
  }),
);
