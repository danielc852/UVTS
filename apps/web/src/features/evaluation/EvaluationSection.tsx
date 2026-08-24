import { Badge } from '@astryxdesign/core/Badge';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { ProgressBar } from '@astryxdesign/core/ProgressBar';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import {
  EvaluationRequestError,
  retryFailedQuestions,
  retryQuestion,
  startEvaluation,
} from '../../api/evaluation';
import { queryKeys } from '../../api/query-keys';
import type { EvaluationItem, Question } from '../../shared/model/workspace';
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

export function EvaluationSection({ state, questions, evaluation, testId }: EvaluationSectionProps) {
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestError, setRequestError] = useState<string>();
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

  const completed = evaluation.filter(
    (item) => item.status === 'complete' || item.status === 'failed',
  ).length;
  const failed = evaluation.filter((item) => item.status === 'failed').length;
  const hasStarted = evaluation.length > 0;

  const run = async (action: () => Promise<import('../../shared/model/workspace').TestWorkspace>) => {
    setIsSubmitting(true);
    setRequestError(undefined);
    try {
      const updated = await action();
      queryClient.setQueryData(queryKeys.test(updated.id), updated);
    } catch (error) {
      setRequestError(
        error instanceof EvaluationRequestError
          ? error.message
          : 'The evaluation request could not be completed. Try again.',
      );
    } finally {
      setIsSubmitting(false);
    }
  };

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
            onClick={() => void run(() => startEvaluation(testId))}
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
              const item = evaluation.find((candidate) => candidate.questionId === question.id);
              const status = item?.status ?? 'waiting';
              return (
                <li key={question.id}>
                  <span>{question.text}</span>
                  <Badge
                    label={statusLabels[status]}
                    variant={
                      status === 'failed'
                        ? 'error'
                        : status === 'checking'
                          ? 'info'
                          : 'neutral'
                    }
                  />
                  {status === 'failed' ? (
                    <Button
                      label={`Retry question ${index + 1}`}
                      variant="ghost"
                      size="sm"
                      isDisabled={isSubmitting || state === 'working'}
                      onClick={() => void run(() => retryQuestion(testId, question.id))}
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
              onClick={() => void run(() => retryFailedQuestions(testId))}
            />
          ) : null}
        </>
      ) : null}
    </StageSection>
  );
}
