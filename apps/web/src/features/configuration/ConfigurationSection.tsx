import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { FileInput } from '@astryxdesign/core/FileInput';
import { FormLayout } from '@astryxdesign/core/FormLayout';
import { NumberInput } from '@astryxdesign/core/NumberInput';
import { TextArea } from '@astryxdesign/core/TextArea';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';

import type { TestConfiguration, WorkspaceError } from '../../entities/workspace/model';
import { storeWorkspace } from '../../entities/workspace/query';
import { StageSection } from '../../shared/ui/StageSection';
import { generateQuestions, QuestionTransitionError } from '../questions/api';
import {
  QuestionConfigurationRequestError,
  saveProductConfiguration,
} from './api';
import {
  configurationSchema,
  MAX_PRODUCT_IMAGE_BYTES,
  type ConfigurationForm,
} from './schema';

const configurationFieldMap = {
  productImage: 'productImage',
  productDescription: 'productDescription',
  totalQuestions: 'totalQuestions',
} as const;

interface ConfigurationSectionProps {
  testId?: string;
  state: 'locked' | 'active' | 'working' | 'complete';
  configuration: TestConfiguration;
  error?: WorkspaceError;
  isLocked?: boolean;
  isBusy?: boolean;
}

export function ConfigurationSection({
  testId,
  state,
  configuration,
  error,
  isLocked = false,
  isBusy = false,
}: ConfigurationSectionProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [requestError, setRequestError] = useState<string>();
  const schema = useMemo(
    () => configurationSchema(Boolean(configuration.productImage)),
    [configuration.productImage],
  );
  const form = useForm<ConfigurationForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      productImage: null,
      productDescription: configuration.productDescription,
      totalQuestions: configuration.totalQuestions,
    },
  });
  const saveMutation = useMutation({
    mutationFn: async (values: ConfigurationForm) => {
      const saved = await saveProductConfiguration({
        testId,
        productImage: values.productImage ?? undefined,
        productDescription: values.productDescription,
        totalQuestions: values.totalQuestions,
      });
      storeWorkspace(queryClient, saved);
      if (!testId) navigate(`/tests/${saved.id}`, { replace: true });
      form.reset({
        productImage: null,
        productDescription: saved.configuration.productDescription,
        totalQuestions: saved.configuration.totalQuestions,
      });
      const generating = await generateQuestions(saved.id);
      storeWorkspace(queryClient, generating);
    },
    onError: (caught: unknown) => {
      if (caught instanceof QuestionConfigurationRequestError) {
        for (const [field, messages] of Object.entries(caught.fieldErrors ?? {})) {
          const formField = configurationFieldMap[field as keyof typeof configurationFieldMap];
          if (formField && messages[0]) form.setError(formField, { message: messages[0] });
        }
        setRequestError(caught.message);
      } else if (caught instanceof QuestionTransitionError) {
        setRequestError(caught.message);
      } else {
        setRequestError('The question setup could not be saved. Try again.');
      }
    },
  });

  if (state === 'locked') {
    return (
      <StageSection
        number={1}
        title="Product setup"
        state="locked"
        lockedText="Start over to change the confirmed product setup."
      />
    );
  }

  const savedSummary =
    configuration.productImage && configuration.productDescription.trim()
      ? `${configuration.totalQuestions} questions · ${configuration.productImage.filename} · description added`
      : undefined;

  if (isLocked) {
    return (
      <StageSection
        number={1}
        title="Product setup"
        state="complete"
        summary={savedSummary}
        error={error}
      >
        <Banner
          status="info"
          title="Product setup locked"
          description="The confirmed questions are tied to this setup. Start over from the Questions step if you deliberately want to change it."
        />
      </StageSection>
    );
  }

  const markDirty = () => {
    setRequestError(undefined);
  };

  const submit = async (values: ConfigurationForm) => {
    setRequestError(undefined);
    await saveMutation.mutateAsync(values).catch(() => undefined);
  };

  return (
    <StageSection number={1} title="Product setup" state={state} summary={savedSummary} error={error}>
      <p>Add the product context UVTS will use to create questions. No manual is needed yet.</p>
      {savedSummary ? <p className="supporting-text">Saved setup: {savedSummary}</p> : null}
      {requestError ? (
        <Banner status="error" title="Questions were not started" description={requestError} />
      ) : null}
      {isBusy ? (
        <Banner
          status="info"
          title="Creating draft questions"
          description="Your product setup is saved. UVTS is creating a draft question set."
        />
      ) : null}
      <form onSubmit={form.handleSubmit(submit)} noValidate>
        <FormLayout direction="vertical" defaultOptionality="required">
          <Controller
            name="productImage"
            control={form.control}
            render={({ field, fieldState }) => (
              <FileInput
                label="Product image"
                value={field.value}
                onChange={(value) => {
                  field.onChange(Array.isArray(value) ? (value[0] ?? null) : value);
                  markDirty();
                }}
                accept="image/*"
                maxSize={MAX_PRODUCT_IMAGE_BYTES}
                mode="dropzone"
                isRequired={!configuration.productImage}
                isOptional={Boolean(configuration.productImage)}
                description={
                  configuration.productImage
                    ? `Current image: ${configuration.productImage.filename}. Choose another image to replace it.`
                    : 'Choose any image file up to 10 MB.'
                }
                status={
                  fieldState.error
                    ? { type: 'error', message: fieldState.error.message }
                    : undefined
                }
                isDisabled={isBusy}
                disabledMessage="Wait for question generation to finish before changing Product setup."
                isLoading={isBusy}
              />
            )}
          />
          <Controller
            name="productDescription"
            control={form.control}
            render={({ field, fieldState }) => (
              <TextArea
                label="Product description"
                value={field.value}
                onChange={(value) => {
                  field.onChange(value);
                  markDirty();
                }}
                rows={5}
                placeholder="Describe what the product is, who uses it, and its main purpose."
                description="Include the details a person would need to ask useful product questions."
                status={
                  fieldState.error
                    ? { type: 'error', message: fieldState.error.message }
                    : undefined
                }
                isDisabled={isBusy}
                disabledMessage="Wait for question generation to finish before changing Product setup."
              />
            )}
          />
          <Controller
            name="totalQuestions"
            control={form.control}
            render={({ field, fieldState }) => (
              <NumberInput
                label="Number of questions"
                value={field.value}
                onChange={(value) => {
                  field.onChange(value);
                  markDirty();
                }}
                min={1}
                max={15}
                isIntegerOnly
                isWheelEnabled={false}
                description="Choose between 1 and 15 questions."
                status={
                  fieldState.error
                    ? { type: 'error', message: 'Enter a number from 1 to 15.' }
                    : undefined
                }
                isDisabled={isBusy}
                disabledMessage="Wait for question generation to finish before changing Product setup."
              />
            )}
          />
          <Button
            label="Save and generate questions"
            variant="primary"
            type="submit"
            isLoading={form.formState.isSubmitting}
            isDisabled={isBusy}
          />
        </FormLayout>
      </form>
    </StageSection>
  );
}
