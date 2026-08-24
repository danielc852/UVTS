import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from '../../api/fixtures/workspaces';
import { renderApp } from '../../test/render-app';

const configurationApi = vi.hoisted(() => ({ save: vi.fn(), generate: vi.fn() }));

vi.mock('../../api/question-configuration', () => ({
  saveProductConfiguration: configurationApi.save,
  QuestionConfigurationRequestError: class QuestionConfigurationRequestError extends Error {
    code = 'question_configuration_request_failed';
    fieldErrors = {};
  },
}));
vi.mock('../../api/questions', () => ({
  generateQuestions: configurationApi.generate,
  QuestionTransitionError: class QuestionTransitionError extends Error {},
}));

function productImageInput(): HTMLInputElement {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error('Product image input not found');
  return input;
}

describe('ConfigurationSection', () => {
  beforeEach(() => {
    configurationApi.save.mockReset();
    configurationApi.generate.mockReset();
  });

  it('opens a clean workspace at Product setup with only product context fields', async () => {
    renderApp('/');

    expect(await screen.findByRole('heading', { name: '1. Product setup' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Product image' })).toBeInTheDocument();
    expect(screen.getByLabelText('Product description')).toBeInTheDocument();
    expect(screen.getByLabelText('Number of questions')).toHaveValue('9');
    expect(screen.queryByText('Question types')).not.toBeInTheDocument();
  });

  it('validates the required image, description, and count before creating a test', async () => {
    const user = userEvent.setup();
    renderApp('/');
    await screen.findByRole('heading', { name: '1. Product setup' });

    await user.click(screen.getByRole('button', { name: 'Save and generate questions' }));

    expect(await screen.findByText('Add a product image before saving the question setup.')).toBeInTheDocument();
    expect(screen.getByText('Describe the product before saving the question setup.')).toBeInTheDocument();
    expect(configurationApi.save).not.toHaveBeenCalled();
  });

  it('updates Product setup and starts generation from the persisted test', async () => {
    const user = userEvent.setup();
    const saved = getWorkspaceFixture('configuration-saved');
    const generating = getWorkspaceFixture('questions-ready');
    expect(saved).toBeDefined();
    expect(generating).toBeDefined();
    configurationApi.save.mockResolvedValue(saved);
    configurationApi.generate.mockResolvedValue(generating);
    renderApp('/tests/configuration-saved');

    expect(await screen.findByText(/Current image: smart-speaker.png/)).toBeInTheDocument();
    const count = screen.getByLabelText('Number of questions');
    await user.clear(count);
    await user.type(count, '8');
    await user.click(screen.getByRole('button', { name: 'Save and generate questions' }));

    await waitFor(() =>
      expect(configurationApi.save).toHaveBeenCalledWith(
        expect.objectContaining({
          testId: 'configuration-saved',
          productImage: undefined,
          totalQuestions: 8,
        }),
      ),
    );
    expect(configurationApi.generate).toHaveBeenCalledWith('configuration-saved');
  });

  it('prevents duplicate submission while the save is pending', async () => {
    const user = userEvent.setup();
    configurationApi.save.mockImplementation(() => new Promise(() => undefined));
    renderApp('/');
    await screen.findByRole('heading', { name: '1. Product setup' });
    await user.upload(productImageInput(), new File(['image'], 'speaker.png', { type: 'image/png' }));
    await user.type(screen.getByLabelText('Product description'), 'A compact smart speaker.');
    await user.click(screen.getByRole('button', { name: 'Save and generate questions' }));

    expect(screen.getByRole('button', { name: 'Save and generate questions' })).toBeDisabled();
    expect(configurationApi.save).toHaveBeenCalledOnce();
  });

  it('restores the generation state after reload and locks setup controls', async () => {
    renderApp('/tests/configuration-generating');

    expect(await screen.findByText('Creating draft questions')).toBeInTheDocument();
    expect(screen.getByLabelText('Product description')).toHaveAttribute('aria-disabled', 'true');
    expect(screen.getByLabelText('Number of questions')).toHaveAttribute('aria-disabled', 'true');
    expect(screen.getByRole('button', { name: 'Save and generate questions' })).toBeDisabled();
  });
});
