import { zodResolver } from '@hookform/resolvers/zod';
import { Button } from '@astryxdesign/core/Button';
import { CheckboxList, CheckboxListItem } from '@astryxdesign/core/CheckboxList';
import { FormLayout } from '@astryxdesign/core/FormLayout';
import { NumberInput } from '@astryxdesign/core/NumberInput';
import { Controller, useForm } from 'react-hook-form';
import { z } from 'zod';

import type { TestConfiguration, WorkspaceError } from '../../shared/model/workspace';
import { StageSection } from '../../shared/ui/StageSection';

const configurationSchema = z
  .object({
    totalQuestions: z.number().int().min(1).max(15),
    questionTypes: z.array(z.string()).min(1),
    topics: z.array(z.string()).min(1),
    viewpoints: z.array(z.string()).min(1),
    basic: z.number().int().min(0),
    crossParagraph: z.number().int().min(0),
    edgeCase: z.number().int().min(0),
  })
  .refine((value) => value.basic + value.crossParagraph + value.edgeCase === value.totalQuestions, {
    message: 'The questions by type must add up to the total.',
    path: ['basic'],
  });

type ConfigurationForm = z.infer<typeof configurationSchema>;

interface ConfigurationSectionProps {
  state: 'locked' | 'active' | 'complete';
  configuration: TestConfiguration;
  error?: WorkspaceError;
}

export function ConfigurationSection({ state, configuration, error }: ConfigurationSectionProps) {
  const form = useForm<ConfigurationForm>({
    resolver: zodResolver(configurationSchema),
    defaultValues: {
      totalQuestions: configuration.totalQuestions,
      questionTypes: ['Basic', 'Cross-paragraph', 'Edge-case'],
      topics: configuration.topics,
      viewpoints: configuration.viewpoints,
      basic: configuration.typeCounts.basic,
      crossParagraph: configuration.typeCounts.crossParagraph,
      edgeCase: configuration.typeCounts.edgeCase,
    },
  });

  if (state === 'locked') {
    return <StageSection number={2} title="Generate questions" state="locked" lockedText="Upload a manual to continue." />;
  }

  return (
    <StageSection
      number={2}
      title="Generate questions"
      state={state}
      summary={
        state === 'complete'
          ? `${configuration.totalQuestions} questions · all relevant topics · all user viewpoints`
          : undefined
      }
      error={error}
    >
      <form onSubmit={form.handleSubmit(() => undefined)} noValidate>
        <FormLayout direction="vertical" defaultOptionality="required">
          <Controller
            name="totalQuestions"
            control={form.control}
            render={({ field, fieldState }) => (
              <NumberInput
                label="Number of questions"
                value={field.value}
                onChange={field.onChange}
                min={1}
                max={15}
                isIntegerOnly
                isWheelEnabled={false}
                status={fieldState.error ? { type: 'error', message: 'Enter a number from 1 to 15.' } : undefined}
              />
            )}
          />
          <Controller
            name="questionTypes"
            control={form.control}
            render={({ field, fieldState }) => (
              <CheckboxList
                label="Question types"
                value={field.value}
                onChange={field.onChange}
                status={fieldState.error ? { type: 'error', message: 'Choose at least one question type.' } : undefined}
              >
                {['Basic', 'Cross-paragraph', 'Edge-case'].map((item) => (
                  <CheckboxListItem key={item} label={item} value={item} />
                ))}
              </CheckboxList>
            )}
          />
          <div className="number-grid" aria-label="Questions by type">
            {(
              [
                ['basic', 'Basic questions'],
                ['crossParagraph', 'Cross-paragraph questions'],
                ['edgeCase', 'Edge-case questions'],
              ] as const
            ).map(([name, label]) => (
              <Controller
                key={name}
                name={name}
                control={form.control}
                render={({ field, fieldState }) => (
                  <NumberInput
                    label={label}
                    value={field.value}
                    onChange={field.onChange}
                    min={0}
                    max={15}
                    isIntegerOnly
                    isWheelEnabled={false}
                    status={fieldState.error ? { type: 'error', message: fieldState.error.message } : undefined}
                  />
                )}
              />
            ))}
          </div>
          <Controller
            name="topics"
            control={form.control}
            render={({ field, fieldState }) => (
              <CheckboxList
                label="Topics"
                value={field.value}
                onChange={field.onChange}
                hasDividers
                status={fieldState.error ? { type: 'error', message: 'Choose at least one topic.' } : undefined}
              >
                {configuration.topics.map((item) => (
                  <CheckboxListItem key={item} label={item} value={item} />
                ))}
              </CheckboxList>
            )}
          />
          <Controller
            name="viewpoints"
            control={form.control}
            render={({ field, fieldState }) => (
              <CheckboxList
                label="User viewpoints"
                value={field.value}
                onChange={field.onChange}
                status={fieldState.error ? { type: 'error', message: 'Choose at least one user viewpoint.' } : undefined}
              >
                {['Beginner', 'Regular user', 'Advanced user'].map((item) => (
                  <CheckboxListItem key={item} label={item} value={item} />
                ))}
              </CheckboxList>
            )}
          />
          <p className="supporting-text">
            {configuration.totalQuestions} questions · 3 Basic · 3 Cross-paragraph · 3 Edge-case
          </p>
          <Button label="Generate questions" variant="primary" type="submit" />
        </FormLayout>
      </form>
    </StageSection>
  );
}
