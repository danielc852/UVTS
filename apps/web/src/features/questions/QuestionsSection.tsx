import { AlertDialog } from '@astryxdesign/core/AlertDialog';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { ProgressBar } from '@astryxdesign/core/ProgressBar';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import {
  confirmQuestions,
  generateQuestions,
  QuestionTransitionError,
  startOver,
} from './api';
import { storeWorkspace } from '../../entities/workspace/query';
import type { TestWorkspace } from '../../entities/workspace/model';
import { StageSection } from '../../shared/ui/StageSection';

interface QuestionsSectionProps {
  state: 'locked' | 'active' | 'working' | 'complete';
  workspace: TestWorkspace;
}

type PendingAction = 'regenerate' | 'start-over';
type QuestionAction = 'confirm' | PendingAction;

function runQuestionAction(testId: string, action: QuestionAction): Promise<TestWorkspace> {
  switch (action) {
    case 'confirm':
      return confirmQuestions(testId);
    case 'regenerate':
      return generateQuestions(testId);
    case 'start-over':
      return startOver(testId);
  }
}

function questionActionError(error: Error | null): string | undefined {
  if (!error) return undefined;
  if (error instanceof QuestionTransitionError) return error.message;
  return 'The question action could not be completed. Try again.';
}

export function QuestionsSection({ state, workspace }: QuestionsSectionProps) {
  const queryClient = useQueryClient();
  const [pendingAction, setPendingAction] = useState<PendingAction>();
  const questionSet = workspace.questionSet;
  const questions = questionSet?.items ?? [];
  const isConfirmed = questionSet?.status === 'confirmed';
  const isLegacy = questionSet?.source === 'legacy_manual_unknown';
  const isStale = questionSet?.configurationVersion !== workspace.configuration.version;
  const actionMutation = useMutation({
    mutationFn: (action: QuestionAction) => runQuestionAction(workspace.id, action),
    onSuccess: (updated) => {
      storeWorkspace(queryClient, updated);
      setPendingAction(undefined);
    },
  });
  const actionError = questionActionError(actionMutation.error);
  const isSubmitting = actionMutation.isPending;

  if (state === 'locked') {
    return (
      <StageSection
        number={2}
        title="Review and confirm questions"
        state="locked"
        lockedText="Save Product setup to generate questions."
      />
    );
  }

  return (
    <StageSection
      number={2}
      title="Review and confirm questions"
      state={state}
      summary={isConfirmed ? `${questions.length} confirmed questions` : undefined}
      error={workspace.error}
    >
      {state === 'working' ? (
        <>
          <ProgressBar label="Generating questions" isIndeterminate />
          <p role="status">Creating a new draft from the saved product image and description…</p>
        </>
      ) : null}
      {actionError ? (
        <Banner status="error" title="Question action failed" description={actionError} />
      ) : null}
      {isLegacy ? (
        <Banner
          status="warning"
          title="Generate a product-only question set"
          description="These saved questions came from the earlier manual-first workflow. Review them if useful, then generate a new set before confirmation."
        />
      ) : null}
      {isStale && !isLegacy && !isConfirmed ? (
        <Banner
          status="warning"
          title="This draft is out of date"
          description="Product setup changed after this draft was generated. Generate again before confirming."
        />
      ) : null}
      {isConfirmed ? (
        <Banner
          status="success"
          title="Questions confirmed"
          description="This exact set is locked for the test. Start over only if you deliberately want to remove its later manual and results."
        />
      ) : (
        <p>Review the complete draft. You can generate another draft until you confirm this set.</p>
      )}
      <ol className="question-list">
        {questions.map((question) => (
          <li key={question.id}>
            <p>{question.text}</p>
          </li>
        ))}
      </ol>
      <div className="action-row">
        {isConfirmed ? (
          <Button
            label="Start over"
            variant="secondary"
            isDisabled={isSubmitting}
            onClick={() => {
              actionMutation.reset();
              setPendingAction('start-over');
            }}
          />
        ) : (
          <>
            <Button
              label={isLegacy ? 'Generate product-only questions' : 'Generate again'}
              variant="secondary"
              isDisabled={state === 'working' || isSubmitting}
              onClick={() => {
                actionMutation.reset();
                setPendingAction('regenerate');
              }}
            />
            <Button
              label="Confirm questions"
              variant="primary"
              isDisabled={state === 'working' || isSubmitting || isLegacy || isStale || questions.length === 0}
              isLoading={isSubmitting && !pendingAction}
              onClick={() => actionMutation.mutate('confirm')}
            />
          </>
        )}
      </div>

      <AlertDialog
        isOpen={Boolean(pendingAction)}
        onOpenChange={(open) => {
          if (!open && !isSubmitting) {
            actionMutation.reset();
            setPendingAction(undefined);
          }
        }}
        title={pendingAction === 'start-over' ? 'Start this test over?' : 'Generate a different draft?'}
        description={
          pendingAction === 'start-over'
            ? 'Product setup will remain. Confirmed questions, the manual, evaluation, and report will be permanently removed.'
            : 'A successful generation will replace the current draft. If generation fails, this draft will remain unchanged.'
        }
        actionLabel={pendingAction === 'start-over' ? 'Start over and remove results' : 'Generate another draft'}
        cancelLabel="Cancel"
        isActionLoading={isSubmitting}
        onAction={() => {
          if (pendingAction) actionMutation.mutate(pendingAction);
        }}
      />
    </StageSection>
  );
}
