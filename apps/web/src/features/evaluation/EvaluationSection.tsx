import { Badge } from '@astryxdesign/core/Badge';
import { Button } from '@astryxdesign/core/Button';
import { ProgressBar } from '@astryxdesign/core/ProgressBar';

import type { EvaluationItem, Question } from '../../shared/model/workspace';
import { StageSection } from '../../shared/ui/StageSection';

interface EvaluationSectionProps {
  state: 'locked' | 'active' | 'working' | 'complete';
  questions: Question[];
  evaluation: EvaluationItem[];
}

const statusLabels = {
  waiting: 'Waiting',
  checking: 'Checking',
  complete: 'Complete',
  failed: 'Failed',
};

export function EvaluationSection({ state, questions, evaluation }: EvaluationSectionProps) {
  if (state === 'locked') {
    return (
      <StageSection
        number={4}
        title="Evaluation"
        state="locked"
        lockedText="Review and evaluate the questions to see progress here."
      />
    );
  }

  const completed = evaluation.filter((item) => item.status === 'complete' || item.status === 'failed').length;
  const failed = evaluation.filter((item) => item.status === 'failed').length;

  return (
    <StageSection
      number={4}
      title="Evaluation"
      state={state}
      summary={state === 'complete' ? `${completed} of ${questions.length} questions checked` : undefined}
    >
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
        {questions.map((question) => {
          const item = evaluation.find((candidate) => candidate.questionId === question.id);
          const status = item?.status ?? 'waiting';
          return (
            <li key={question.id}>
              <span>{question.text}</span>
              <Badge
                label={statusLabels[status]}
                variant={status === 'failed' ? 'error' : status === 'checking' ? 'info' : 'neutral'}
              />
            </li>
          );
        })}
      </ol>
      {failed > 0 ? <Button label="Retry failed questions" variant="secondary" /> : null}
    </StageSection>
  );
}
