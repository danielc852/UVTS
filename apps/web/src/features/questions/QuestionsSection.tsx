import { Badge } from '@astryxdesign/core/Badge';
import { Button } from '@astryxdesign/core/Button';

import type { Question } from '../../shared/model/workspace';
import { StageSection } from '../../shared/ui/StageSection';

interface QuestionsSectionProps {
  state: 'locked' | 'active' | 'complete';
  questions: Question[];
}

export function QuestionsSection({ state, questions }: QuestionsSectionProps) {
  if (state === 'locked') {
    return (
      <StageSection
        number={3}
        title="Review questions"
        state="locked"
        lockedText="Generate questions to review them here."
      />
    );
  }

  return (
    <StageSection
      number={3}
      title="Review questions"
      state={state}
      summary={state === 'complete' ? `${questions.length} questions reviewed` : undefined}
    >
      <p>Review the complete set. Questions cannot change after evaluation starts.</p>
      <ol className="question-list">
        {questions.map((question) => (
          <li key={question.id}>
            <p>{question.text}</p>
            <div className="metadata-row">
              <Badge label={question.type} variant="neutral" />
              <span>{question.topic}</span>
              <span>{question.viewpoint}</span>
            </div>
          </li>
        ))}
      </ol>
      <div className="action-row">
        <Button label="Generate again" variant="secondary" />
        <Button label="Evaluate questions" variant="primary" />
      </div>
    </StageSection>
  );
}
