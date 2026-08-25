import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { FormLayout } from '@astryxdesign/core/FormLayout';
import {
  HStack,
  Layout,
  LayoutContent,
  LayoutFooter,
} from '@astryxdesign/core/Layout';
import { TextArea } from '@astryxdesign/core/TextArea';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';

import { QuestionTransitionError, suggestQuestion } from './api';

interface QuestionSuggestionDialogProps {
  existingQuestions: string[];
  isOpen: boolean;
  onAdd: (question: string) => void;
  onOpenChange: (isOpen: boolean) => void;
  testId: string;
}

const maximumDirectionLength = 1_000;

function suggestionError(error: Error | null): string | undefined {
  if (!error) return undefined;
  if (error instanceof QuestionTransitionError) return error.message;
  return 'The question could not be generated. Try again.';
}

export function QuestionSuggestionDialog({
  existingQuestions,
  isOpen,
  onAdd,
  onOpenChange,
  testId,
}: QuestionSuggestionDialogProps) {
  const [direction, setDirection] = useState('');
  const [wasSubmitted, setWasSubmitted] = useState(false);
  const mutation = useMutation({
    mutationFn: () => suggestQuestion(testId, direction.trim(), existingQuestions),
    onSuccess: (question) => {
      onAdd(question);
      setDirection('');
      setWasSubmitted(false);
      onOpenChange(false);
    },
  });
  const isBlank = !direction.trim();
  const isTooLong = direction.length > maximumDirectionLength;
  const error = suggestionError(mutation.error);

  const changeOpen = (open: boolean) => {
    if (!open && mutation.isPending) return;
    if (!open) {
      mutation.reset();
      setDirection('');
      setWasSubmitted(false);
    }
    onOpenChange(open);
  };

  return (
    <Dialog
      isOpen={isOpen}
      onOpenChange={changeOpen}
      purpose="form"
      width={560}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setWasSubmitted(true);
          if (isBlank || isTooLong) return;
          mutation.mutate();
        }}
      >
        <Layout
          height="auto"
          header={
            <DialogHeader
              title="Generate a question with AI"
              subtitle="Give UVTS a topic or situation. You can edit the generated question before confirming the set."
              onOpenChange={changeOpen}
            />
          }
          content={
            <LayoutContent>
              <FormLayout direction="vertical" defaultOptionality="required">
                {error ? (
                  <Banner
                    status="error"
                    title="Question generation failed"
                    description={error}
                  />
                ) : null}
                <TextArea
                  label="Direction for the question"
                  description="For example: Ask about using the product outdoors in bad weather."
                  value={direction}
                  onChange={(value) => {
                    mutation.reset();
                    setDirection(value);
                  }}
                  rows={4}
                  maxLength={maximumDirectionLength}
                  width="100%"
                  isRequired
                  isDisabled={mutation.isPending}
                  disabledMessage="Wait for UVTS to finish generating the question."
                  status={
                    wasSubmitted && isBlank
                      ? { type: 'error', message: 'Enter a direction for the question.' }
                      : isTooLong
                        ? {
                            type: 'error',
                            message: 'Keep the direction within 1,000 characters.',
                          }
                        : undefined
                  }
                  statusVariant="detached"
                />
              </FormLayout>
            </LayoutContent>
          }
          footer={
            <LayoutFooter hasDivider>
              <HStack gap={2} hAlign="end" wrap="wrap">
                <Button
                  label="Cancel"
                  variant="secondary"
                  type="button"
                  isDisabled={mutation.isPending}
                  onClick={() => changeOpen(false)}
                />
                <Button
                  label="Generate question"
                  variant="primary"
                  type="submit"
                  isLoading={mutation.isPending}
                  isDisabled={mutation.isPending || isTooLong}
                />
              </HStack>
            </LayoutFooter>
          }
        />
      </form>
    </Dialog>
  );
}
