import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from '../../api/fixtures/workspaces';
import { renderApp } from '../../test/render-app';

const questionApi = vi.hoisted(() => ({
  confirm: vi.fn(),
  generate: vi.fn(),
  startOver: vi.fn(),
}));

vi.mock('../../api/questions', () => ({
  confirmQuestions: questionApi.confirm,
  generateQuestions: questionApi.generate,
  startOver: questionApi.startOver,
  QuestionTransitionError: class QuestionTransitionError extends Error {},
}));

describe('QuestionsSection', () => {
  beforeEach(() => {
    questionApi.confirm.mockReset();
    questionApi.generate.mockReset();
    questionApi.startOver.mockReset();
  });

  it('persists confirmation and advances to Upload manual', async () => {
    const user = userEvent.setup();
    const uploadReady = getWorkspaceFixture('upload-ready');
    questionApi.confirm.mockResolvedValue(
      uploadReady ? { ...uploadReady, id: 'questions-ready' } : uploadReady,
    );
    renderApp('/tests/questions-ready');

    await user.click(await screen.findByRole('button', { name: 'Confirm questions' }));

    expect(questionApi.confirm).toHaveBeenCalledWith('questions-ready');
    expect(await screen.findByRole('heading', { name: '3. Upload manual' })).toBeInTheDocument();
  });

  it('requires an explicit dialog before replacing a draft', async () => {
    const user = userEvent.setup();
    const regenerated = getWorkspaceFixture('questions-ready');
    questionApi.generate.mockResolvedValue(regenerated);
    renderApp('/tests/questions-ready');

    await user.click(await screen.findByRole('button', { name: 'Generate again' }));

    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(questionApi.generate).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Generate another draft' }));
    expect(questionApi.generate).toHaveBeenCalledWith('questions-ready');
  });

  it('states exactly what Start over preserves and removes', async () => {
    const user = userEvent.setup();
    renderApp('/tests/upload-ready');
    await screen.findByRole('heading', { name: '3. Upload manual' });
    await user.click(
      screen.getByRole('button', { name: 'Review and confirm questionsComplete' }),
    );

    await user.click(await screen.findByRole('button', { name: 'Start over' }));

    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByText(/Product setup will remain/)).toBeInTheDocument();
    expect(screen.getByText(/Confirmed questions, the manual, evaluation, and report/)).toBeInTheDocument();
  });

  it('requires product-only regeneration for a preserved legacy draft', async () => {
    renderApp('/tests/legacy-questions');

    expect(await screen.findByText('Generate a product-only question set')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm questions' })).toBeDisabled();
    expect(
      screen.getByRole('button', { name: 'Generate product-only questions' }),
    ).toBeEnabled();
  });

  it('keeps the previous draft visible while regeneration is running', async () => {
    renderApp('/tests/questions-generating');

    expect(await screen.findByRole('progressbar', { name: 'Generating questions' })).toBeInTheDocument();
    expect(screen.getAllByText(/How do I complete the initial setup/).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Generate again' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Confirm questions' })).toBeDisabled();
  });

  it('recovers from a failed confirmation without losing the draft', async () => {
    const user = userEvent.setup();
    questionApi.confirm.mockRejectedValue(new Error('network unavailable'));
    renderApp('/tests/questions-ready');

    await user.click(await screen.findByRole('button', { name: 'Confirm questions' }));

    expect(await screen.findByText(/question action could not be completed/i)).toBeInTheDocument();
    expect(screen.getAllByText(/How do I complete the initial setup/).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Confirm questions' })).toBeEnabled();
  });
});
