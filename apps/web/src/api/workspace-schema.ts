import { z } from 'zod';

import type { TestWorkspace } from '../shared/model/workspace';

const questionSchema = z.object({
  id: z.string(),
  text: z.string(),
  type: z.enum(['Basic', 'Cross-paragraph', 'Edge-case']),
  topic: z.string(),
  viewpoint: z.enum(['Beginner', 'Regular user', 'Advanced user']),
});

const evaluationItemSchema = z.object({
  questionId: z.string(),
  status: z.enum(['waiting', 'checking', 'complete', 'failed']),
  error: z.string().nullish().transform((value) => value ?? undefined),
});

const resultSchema = z.object({
  question: questionSchema,
  status: z.enum(['found', 'partly_found', 'not_found', 'failed']),
  informationNeeded: z.string(),
  informationFound: z.string().nullish().transform((value) => value ?? undefined),
  informationMissing: z.string().nullish().transform((value) => value ?? undefined),
  evidence: z.array(z.object({ page: z.number().int().positive(), extract: z.string() })).default([]),
});

export const workspaceStateSchema: z.ZodType<TestWorkspace> = z.object({
  id: z.string(),
  currentStage: z.enum(['upload', 'configuration', 'questions', 'evaluation', 'report']),
  manual: z
    .object({
      id: z.string(),
      filename: z.string(),
      pageCount: z.number().int().positive(),
      status: z.enum(['checking', 'ready', 'invalid']),
    })
    .optional(),
  configuration: z.object({
    totalQuestions: z.number().int().min(1).max(15),
    typeCounts: z.object({
      basic: z.number().int().nonnegative(),
      crossParagraph: z.number().int().nonnegative(),
      edgeCase: z.number().int().nonnegative(),
    }),
    topics: z.array(z.string()),
    viewpoints: z.array(z.string()),
  }),
  questions: z.array(questionSchema),
  evaluation: z.array(evaluationItemSchema),
  report: z
    .object({
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
    })
    .optional(),
  error: z
    .object({
      title: z.string(),
      message: z.string(),
      stage: z.enum(['upload', 'configuration', 'questions', 'evaluation', 'report']),
    })
    .optional(),
});
