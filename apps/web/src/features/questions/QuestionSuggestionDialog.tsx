import { Button } from '@astryxdesign/core/Button';
import { Dialog, DialogHeader } from '@astryxdesign/core/Dialog';
import { FormLayout } from '@astryxdesign/core/FormLayout';
import {
  HStack,
  Layout,
  LayoutContent,
  LayoutFooter,
} from '@astryxdesign/core/Layout';
import {
  SegmentedControl,
  SegmentedControlItem,
} from '@astryxdesign/core/SegmentedControl';
import { TextArea } from '@astryxdesign/core/TextArea';
import { useState } from 'react';

interface QuestionSuggestionDialogProps {
  isOpen: boolean;
  onAddManual: (question: string) => void;
  onGenerate: (direction: string) => void;
  onOpenChange: (isOpen: boolean) => void;
}

type QuestionMethod = 'ai' | 'manual';

const maximumLength = 1_000;

export function QuestionSuggestionDialog({
  isOpen,
  onAddManual,
  onGenerate,
  onOpenChange,
}: QuestionSuggestionDialogProps) {
  const [method, setMethod] = useState<QuestionMethod>('ai');
  const [value, setValue] = useState('');
  const [wasSubmitted, setWasSubmitted] = useState(false);
  const isBlank = !value.trim();
  const isTooLong = value.length > maximumLength;

  const reset = () => {
    setMethod('ai');
    setValue('');
    setWasSubmitted(false);
  };

  const changeOpen = (open: boolean) => {
    if (!open) reset();
    onOpenChange(open);
  };

  return (
    <Dialog isOpen={isOpen} onOpenChange={changeOpen} purpose="form" width={560}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setWasSubmitted(true);
          if (isBlank || isTooLong) return;

          const trimmedValue = value.trim();
          if (method === 'ai') onGenerate(trimmedValue);
          else onAddManual(trimmedValue);
          changeOpen(false);
        }}
      >
        <Layout
          height="auto"
          header={
            <DialogHeader
              title="Add a question"
              subtitle="Write the question yourself or give AI a direction. Every added question can be edited before confirmation."
              onOpenChange={changeOpen}
            />
          }
          content={
            <LayoutContent>
              <FormLayout direction="vertical" defaultOptionality="required">
                <SegmentedControl
                  value={method}
                  onChange={(nextMethod) => {
                    setMethod(nextMethod as QuestionMethod);
                    setValue('');
                    setWasSubmitted(false);
                  }}
                  label="Question method"
                  layout="fill"
                >
                  <SegmentedControlItem value="ai" label="Generate with AI" />
                  <SegmentedControlItem value="manual" label="Write manually" />
                </SegmentedControl>
                <TextArea
                  label={method === 'ai' ? 'Direction for the question' : 'Question'}
                  description={
                    method === 'ai'
                      ? 'For example: Ask about using the product outdoors in bad weather.'
                      : 'Write the complete question. You can edit it again in the question list.'
                  }
                  value={value}
                  onChange={setValue}
                  rows={4}
                  maxLength={maximumLength}
                  width="100%"
                  isRequired
                  status={
                    wasSubmitted && isBlank
                      ? {
                          type: 'error',
                          message:
                            method === 'ai'
                              ? 'Enter a direction for the question.'
                              : 'Enter a question.',
                        }
                      : isTooLong
                        ? { type: 'error', message: 'Keep this within 1,000 characters.' }
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
                  onClick={() => changeOpen(false)}
                />
                <Button
                  label={method === 'ai' ? 'Generate question' : 'Add question'}
                  variant="primary"
                  type="submit"
                  isDisabled={isTooLong}
                />
              </HStack>
            </LayoutFooter>
          }
        />
      </form>
    </Dialog>
  );
}
