import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { ProgressBar } from '@astryxdesign/core/ProgressBar';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';

import {
  EvaluationRequestError,
  retryFailedQuestions,
  retryQuestion,
  startEvaluation,
} from './api';
import { storeWorkspace } from '../../entities/workspace/query';
import type {
  EvaluationItem,
  EvaluationStatus,
  Question,
  TestWorkspace,
} from '../../entities/workspace/model';
import { StageSection } from '../../shared/ui/StageSection';

interface EvaluationSectionProps {
  state: 'locked' | 'active' | 'working' | 'complete';
  questions: Question[];
  evaluation: EvaluationItem[];
  testId: string;
}

const statusLabels = {
  waiting: 'Waiting',
  checking: 'Checking',
  complete: 'Complete',
  failed: 'Failed',
};

const statusVariants: Record<EvaluationStatus, 'error' | 'info' | 'neutral'> = {
  waiting: 'neutral',
  checking: 'info',
  complete: 'neutral',
  failed: 'error',
};

function evaluationActionError(error: Error | null): string | undefined {
  if (!error) return undefined;
  if (error instanceof EvaluationRequestError) return error.message;
  return 'The evaluation request could not be completed. Try again.';
}

function summarizeEvaluation(evaluation: EvaluationItem[]): {
  completed: number;
  failed: number;
} {
  let completed = 0;
  let failed = 0;

  for (const item of evaluation) {
    if (item.status === 'complete' || item.status === 'failed') completed += 1;
    if (item.status === 'failed') failed += 1;
  }

  return { completed, failed };
}

export function EvaluationSection({ state, questions, evaluation, testId }: EvaluationSectionProps) {
  const queryClient = useQueryClient();
  const evaluationByQuestion = useMemo(
    () => new Map(evaluation.map((item) => [item.questionId, item])),
    [evaluation],
  );
  const actionMutation = useMutation({
    mutationFn: (action: () => Promise<TestWorkspace>) => action(),
    onSuccess: (updated) => storeWorkspace(queryClient, updated),
  });
  const requestError = evaluationActionError(actionMutation.error);
  const isSubmitting = actionMutation.isPending;
  if (state === 'locked') {
    return (
      <StageSection
        number={4}
        title="Evaluation"
        state="locked"
        lockedText="Confirm the questions and upload a ready manual to begin evaluation."
      />
    );
  }

  const { completed, failed } = summarizeEvaluation(evaluation);
  const hasStarted = evaluation.length > 0;

  return (
    <StageSection
      number={4}
      title="Evaluation"
      state={state}
      summary={
        state === 'complete' ? `${completed} of ${questions.length} questions checked` : undefined
      }
    >
      {requestError ? (
        <Banner status="error" title="Evaluation action failed" description={requestError} />
      ) : null}
      {!hasStarted ? (
        <>
          <p>
            The confirmed questions will be checked against the uploaded manual. Only the manual
            can provide evidence.
          </p>
          <Button
            label="Evaluate confirmed questions"
            variant="primary"
            isLoading={isSubmitting}
            onClick={() => actionMutation.mutate(() => startEvaluation(testId))}
          />
        </>
      ) : null}
      {hasStarted ? (
        <>
          <ProgressBar
            label="Questions checked"
            value={completed}
            max={questions.length || 1}
            hasValueLabel
            formatValueLabel={(value, max) => `${value} of ${max}`}
          />
          <p aria-live="polite">
            {completed} of {questions.length} questions checked
          </p>
          <ol className="evaluation-list">
            {questions.map((question, index) => {
              const item = evaluationByQuestion.get(question.id);
              const status = item?.status ?? 'waiting';
              return (
                <li key={question.id}>
                  <span>{question.text}</span>
                  <Badge
                    label={statusLabels[status]}
                    variant={statusVariants[status]}
                  />
                  {status === 'failed' ? (
                    <Button
                      label={`Retry question ${index + 1}`}
                      variant="ghost"
                      size="sm"
                      isDisabled={isSubmitting || state === 'working'}
                      onClick={() =>
                        actionMutation.mutate(() => retryQuestion(testId, question.id))
                      }
                    />
                  ) : null}
                </li>
              );
            })}
          </ol>
          {failed > 0 ? (
            <Button
              label="Retry failed questions"
              variant="secondary"
              isLoading={isSubmitting}
              isDisabled={state === 'working'}
              onClick={() => actionMutation.mutate(() => retryFailedQuestions(testId))}
            />
          ) : null}
        </>
      ) : null}
    </StageSection>
  );
}
