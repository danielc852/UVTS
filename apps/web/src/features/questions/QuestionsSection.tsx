import { AlertDialog } from '@astryxdesign/core/AlertDialog';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { ProgressBar } from '@astryxdesign/core/ProgressBar';
import { TextArea } from '@astryxdesign/core/TextArea';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import {
  confirmQuestions,
  type ConfirmQuestionItem,
  generateQuestions,
  QuestionTransitionError,
  suggestQuestion,
  startOver,
} from './api';
import { QuestionSuggestionDialog } from './QuestionSuggestionDialog';
import { storeWorkspace } from '../../entities/workspace/query';
import type { TestWorkspace } from '../../entities/workspace/model';
import { StageSection } from '../../shared/ui/StageSection';

interface QuestionsSectionProps {
  state: 'locked' | 'active' | 'working' | 'complete';
  workspace: TestWorkspace;
}

type PendingAction = 'regenerate' | 'start-over';
type QuestionAction =
  | { type: 'confirm'; items: ConfirmQuestionItem[] }
  | { type: PendingAction };
interface QuestionSuggestionRequest {
  clientId: string;
  direction: string;
  existingQuestions: string[];
}

function runQuestionAction(testId: string, action: QuestionAction): Promise<TestWorkspace> {
  switch (action.type) {
    case 'confirm':
      return confirmQuestions(testId, action.items);
    case 'regenerate':
      return generateQuestions(testId);
    case 'start-over':
      return startOver(testId);
  }
}

interface EditableQuestion extends ConfirmQuestionItem {
  clientId: string;
  generation?: {
    error?: string;
    isPending: boolean;
  };
}

const maximumQuestions = 15;
const emptyQuestions: TestWorkspace['questions'] = [];

function createEditableQuestions(
  questions: TestWorkspace['questions'],
): EditableQuestion[] {
  return questions.map((question) => ({
    clientId: `existing-${question.id}`,
    id: question.id,
    text: question.text,
  }));
}

function normalizeQuestion(text: string): string {
  return text
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}_]+/gu, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function questionErrors(questions: EditableQuestion[]): Array<string | undefined> {
  const normalizedCounts = new Map<string, number>();
  for (const question of questions) {
    const normalized = normalizeQuestion(question.text);
    if (normalized) normalizedCounts.set(normalized, (normalizedCounts.get(normalized) ?? 0) + 1);
  }

  return questions.map((question) => {
    if (question.generation?.isPending) return undefined;
    if (question.generation?.error && !question.text.trim()) return question.generation.error;
    const normalized = normalizeQuestion(question.text);
    if (!question.text.trim()) return 'Enter a question before confirming.';
    if (!normalized) return 'Use at least one letter or number.';
    if ((normalizedCounts.get(normalized) ?? 0) > 1) return 'Each question must be unique.';
    return undefined;
  });
}

function mergeQuestionErrors(
  clientErrors: Array<string | undefined>,
  error: Error | null,
): Array<string | undefined> {
  if (!(error instanceof QuestionTransitionError) || !error.fieldErrors) return clientErrors;
  return clientErrors.map(
    (clientError, index) =>
      clientError ?? error.fieldErrors?.[`items.${index}.text`]?.[0],
  );
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
  const questions = questionSet?.items ?? emptyQuestions;
  const isConfirmed = questionSet?.status === 'confirmed';
  const isLegacy = questionSet?.source === 'legacy_manual_unknown';
  const isStale = questionSet?.configurationVersion !== workspace.configuration.version;
  const [editableQuestions, setEditableQuestions] = useState(() => createEditableQuestions(questions));
  const nextClientId = useRef(1);
  const addedQuestionRef = useRef<HTMLTextAreaElement>(null);
  const [addedQuestionClientId, setAddedQuestionClientId] = useState<string>();
  const [isSuggestionOpen, setIsSuggestionOpen] = useState(false);
  useEffect(() => {
    if (addedQuestionClientId) addedQuestionRef.current?.focus();
  }, [addedQuestionClientId]);
  const clientValidationErrors = questionErrors(editableQuestions);
  const isAtQuestionLimit = editableQuestions.length >= maximumQuestions;
  const actionMutation = useMutation({
    mutationFn: (action: QuestionAction) => runQuestionAction(workspace.id, action),
    onSuccess: (updated) => {
      storeWorkspace(queryClient, updated);
      setPendingAction(undefined);
    },
  });
  const suggestionMutation = useMutation({
    mutationFn: ({
      direction,
      existingQuestions,
    }: QuestionSuggestionRequest) => suggestQuestion(workspace.id, direction, existingQuestions),
    onSuccess: (text, { clientId }) => {
      setEditableQuestions((current) =>
        current.map((question) =>
          question.clientId === clientId
            ? { ...question, text, generation: undefined }
            : question,
        ),
      );
    },
    onError: (error, { clientId }) => {
      setEditableQuestions((current) =>
        current.map((question) =>
          question.clientId === clientId
            ? {
                ...question,
                generation: {
                  isPending: false,
                  error:
                    error instanceof QuestionTransitionError
                      ? error.message
                      : 'The question could not be generated. Write it manually or try again.',
                },
              }
            : question,
        ),
      );
    },
  });
  const validationErrors = mergeQuestionErrors(clientValidationErrors, actionMutation.error);
  const hasValidationErrors = validationErrors.some(Boolean);
  const actionError = questionActionError(actionMutation.error);
  const isSubmitting = actionMutation.isPending;
  const hasPendingSuggestion = editableQuestions.some(
    (question) => question.generation?.isPending,
  );

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

  if (state === 'working' && !questionSet) {
    return (
      <StageSection
        number={2}
        title="Review and confirm questions"
        state="working"
        error={workspace.error}
      >
        <ProgressBar label="Generating questions" isIndeterminate />
        <p role="status">Creating a new draft from the saved product image and description…</p>
      </StageSection>
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
      {isConfirmed ? (
        <>
          <div
            className="question-list-scroll"
            role="region"
            aria-label="Confirmed question list"
            tabIndex={0}
          >
            <ol className="question-list">
              {questions.map((question) => (
                <li key={question.id}>
                  <p>{question.text}</p>
                </li>
              ))}
            </ol>
          </div>
          <div className="action-row">
            <Button
              label="Start over"
              variant="secondary"
              isDisabled={isSubmitting}
              onClick={() => {
                actionMutation.reset();
                setPendingAction('start-over');
              }}
            />
          </div>
        </>
      ) : (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (hasPendingSuggestion || hasValidationErrors || editableQuestions.length === 0) return;
            actionMutation.mutate({
              type: 'confirm',
              items: editableQuestions.map(({ id, text }) => ({ id, text: text.trim() })),
            });
          }}
        >
          <div
            className="question-list-scroll"
            role="region"
            aria-label="Editable question list"
            tabIndex={0}
          >
            <ol className="question-list question-editor-list">
              {editableQuestions.map((question, index) => (
                <li key={question.clientId}>
                  <TextArea
                    ref={question.clientId === addedQuestionClientId ? addedQuestionRef : undefined}
                    label={`Question ${index + 1}`}
                    value={question.text}
                    onChange={(text) => {
                      actionMutation.reset();
                      setEditableQuestions((current) =>
                        current.map((item) =>
                          item.clientId === question.clientId ? { ...item, text } : item,
                        ),
                      );
                    }}
                    rows={3}
                    width="100%"
                    isDisabled={state === 'working' || isSubmitting}
                    isReadOnly={question.generation?.isPending}
                    isLoading={question.generation?.isPending}
                    placeholder={
                      question.generation?.isPending
                        ? 'AI is generating this question…'
                        : undefined
                    }
                    disabledMessage="Wait for the current question action to finish."
                    status={
                      validationErrors[index]
                        ? { type: 'error', message: validationErrors[index] }
                        : undefined
                    }
                    statusVariant="detached"
                  />
                  {question.generation?.isPending ? (
                    <p className="question-generation-status" role="status">
                      AI is generating question {index + 1}. You can keep editing other questions.
                    </p>
                  ) : null}
                </li>
              ))}
            </ol>
          </div>
          <div className="action-row question-editor-actions">
            <Button
              label="Add question"
              variant="secondary"
              type="button"
              isDisabled={state === 'working' || isSubmitting || isAtQuestionLimit}
              tooltip={isAtQuestionLimit ? 'You can confirm up to 15 questions.' : undefined}
              onClick={() => {
                actionMutation.reset();
                setIsSuggestionOpen(true);
              }}
            />
            <Button
              label={isLegacy ? 'Generate product-only questions' : 'Generate again'}
              variant="secondary"
              type="button"
              isDisabled={state === 'working' || isSubmitting}
              onClick={() => {
                actionMutation.reset();
                setPendingAction('regenerate');
              }}
            />
            <Button
              label="Confirm questions"
              variant="primary"
              type="submit"
              isDisabled={
                state === 'working' ||
                isSubmitting ||
                isLegacy ||
                isStale ||
                editableQuestions.length === 0 ||
                hasPendingSuggestion ||
                hasValidationErrors
              }
              isLoading={isSubmitting && !pendingAction}
            />
          </div>
        </form>
      )}

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
          if (pendingAction) actionMutation.mutate({ type: pendingAction });
        }}
      />
      <QuestionSuggestionDialog
        isOpen={isSuggestionOpen}
        onOpenChange={setIsSuggestionOpen}
        onAddManual={(text) => {
          actionMutation.reset();
          const clientId = `new-${nextClientId.current++}`;
          setEditableQuestions((current) => [...current, { clientId, text }]);
          setAddedQuestionClientId(clientId);
        }}
        onGenerate={(direction) => {
          actionMutation.reset();
          const clientId = `new-${nextClientId.current++}`;
          const existingQuestions = editableQuestions.map((question) => question.text);
          setEditableQuestions((current) => [
            ...current,
            { clientId, text: '', generation: { isPending: true } },
          ]);
          suggestionMutation.mutate({ clientId, direction, existingQuestions });
        }}
      />
    </StageSection>
  );
}
