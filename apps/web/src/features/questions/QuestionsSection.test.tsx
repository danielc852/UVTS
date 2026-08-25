import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from '../../mocks/workspaces';
import { renderApp } from '../../test/render-app';

const questionApi = vi.hoisted(() => ({
  confirm: vi.fn(),
  generate: vi.fn(),
  startOver: vi.fn(),
  suggest: vi.fn(),
  QuestionTransitionError: class QuestionTransitionError extends Error {
    constructor(
      message: string,
      readonly code = 'question_transition_failed',
      readonly fieldErrors?: Record<string, string[]>,
    ) {
      super(message);
    }
  },
}));

vi.mock('./api', () => ({
  confirmQuestions: questionApi.confirm,
  generateQuestions: questionApi.generate,
  startOver: questionApi.startOver,
  suggestQuestion: questionApi.suggest,
  QuestionTransitionError: questionApi.QuestionTransitionError,
}));

describe('QuestionsSection', () => {
  beforeEach(() => {
    questionApi.confirm.mockReset();
    questionApi.generate.mockReset();
    questionApi.startOver.mockReset();
    questionApi.suggest.mockReset();
  });

  it('persists confirmation and advances to Upload manual', async () => {
    const user = userEvent.setup();
    const uploadReady = getWorkspaceFixture('upload-ready');
    questionApi.confirm.mockResolvedValue(
      uploadReady ? { ...uploadReady, id: 'questions-ready' } : uploadReady,
    );
    renderApp('/tests/questions-ready');

    await user.click(await screen.findByRole('button', { name: 'Confirm questions' }));

    expect(questionApi.confirm).toHaveBeenCalledWith(
      'questions-ready',
      expect.arrayContaining([
        { id: 'q1', text: 'How do I complete the initial setup? (1)' },
      ]),
    );
    expect(await screen.findByRole('heading', { name: 'Upload manual' })).toBeInTheDocument();
  });

  it('keeps the editable question list in a labeled scroll region', async () => {
    renderApp('/tests/questions-ready');

    const scrollRegion = await screen.findByRole('region', {
      name: 'Editable question list',
    });

    expect(scrollRegion).toHaveClass('question-list-scroll');
    expect(scrollRegion).toHaveAttribute('tabindex', '0');
    expect(scrollRegion.querySelector('ol')).toHaveClass('question-list');
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

  it('edits existing questions and appends trimmed questions for confirmation', async () => {
    const user = userEvent.setup();
    questionApi.confirm.mockResolvedValue(getWorkspaceFixture('upload-ready'));
    renderApp('/tests/questions-ready');

    const firstQuestion = await screen.findByRole('textbox', { name: 'Question 1' });
    await user.clear(firstQuestion);
    await user.type(firstQuestion, '  How do I pair the speaker?  ');
    await user.click(screen.getByRole('button', { name: 'Add question' }));
    const dialog = screen.getByRole('dialog');
    await user.click(within(dialog).getByRole('radio', { name: 'Write manually' }));
    await user.type(within(dialog).getByRole('textbox', { name: 'Question' }), '  Is a reset reversible?  ');
    await user.click(within(dialog).getByRole('button', { name: 'Add question' }));
    const addedQuestion = screen.getByRole('textbox', { name: 'Question 10' });
    expect(addedQuestion).toHaveFocus();
    await user.click(screen.getByRole('button', { name: 'Confirm questions' }));

    const submittedItems = questionApi.confirm.mock.calls[0][1];
    expect(submittedItems).toHaveLength(10);
    expect(submittedItems[0]).toEqual({ id: 'q1', text: 'How do I pair the speaker?' });
    expect(submittedItems[9]).toEqual({ id: undefined, text: 'Is a reset reversible?' });
  });

  it('adds an AI loading row without blocking edits to other questions', async () => {
    const user = userEvent.setup();
    let resolveSuggestion!: (question: string) => void;
    questionApi.suggest.mockReturnValue(
      new Promise<string>((resolve) => {
        resolveSuggestion = resolve;
      }),
    );
    renderApp('/tests/questions-ready');

    await user.click(await screen.findByRole('button', { name: 'Add question' }));
    const dialog = screen.getByRole('dialog');
    await user.type(
      within(dialog).getByRole('textbox', { name: 'Direction for the question' }),
      'Ask about using the product during a power outage.',
    );
    await user.click(within(dialog).getByRole('button', { name: 'Generate question' }));

    expect(questionApi.suggest).toHaveBeenCalledWith(
      'questions-ready',
      'Ask about using the product during a power outage.',
      expect.arrayContaining(['How do I complete the initial setup? (1)']),
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByText(/AI is generating question 10/)).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Question 10' })).toHaveAttribute(
      'readonly',
    );
    const firstQuestion = screen.getByRole('textbox', { name: 'Question 1' });
    expect(firstQuestion).toBeEnabled();
    await user.clear(firstQuestion);
    await user.type(firstQuestion, 'Keep editing while AI works');

    resolveSuggestion('Can I use the speaker during a power outage?');
    const generated = await screen.findByRole('textbox', { name: 'Question 10' });
    expect(generated).toHaveValue('Can I use the speaker during a power outage?');
    expect(firstQuestion).toHaveValue('Keep editing while AI works');
  });

  it('keeps manual question entry in the same add-question dialog', async () => {
    const user = userEvent.setup();
    renderApp('/tests/questions-ready');

    await user.click(await screen.findByRole('button', { name: 'Add question' }));
    const dialog = screen.getByRole('dialog');
    expect(within(dialog).getByRole('radio', { name: 'Generate with AI' })).toBeChecked();
    await user.click(within(dialog).getByRole('radio', { name: 'Write manually' }));
    await user.type(
      within(dialog).getByRole('textbox', { name: 'Question' }),
      'Can I replace the battery?',
    );
    await user.click(within(dialog).getByRole('button', { name: 'Add question' }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Question 10' })).toHaveValue(
      'Can I replace the battery?',
    );
  });

  it('shows inline errors for blank and duplicate questions', async () => {
    const user = userEvent.setup();
    renderApp('/tests/questions-ready');

    await user.clear(await screen.findByRole('textbox', { name: 'Question 1' }));
    expect(screen.getByText('Enter a question before confirming.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm questions' })).toBeDisabled();

    await user.type(
      screen.getByRole('textbox', { name: 'Question 1' }),
      'CAN I CHANGE THE EXPORT FORMAT AFTER AUTOMATIC BACKUP IS ENABLED 2',
    );
    expect(screen.getAllByText('Each question must be unique.')).toHaveLength(2);
    expect(screen.getByRole('button', { name: 'Confirm questions' })).toBeDisabled();
  });

  it('rejects punctuation-only questions and maps server validation to the matching field', async () => {
    const user = userEvent.setup();
    renderApp('/tests/questions-ready');

    const firstQuestion = await screen.findByRole('textbox', { name: 'Question 1' });
    await user.clear(firstQuestion);
    await user.type(firstQuestion, '???');
    expect(screen.getAllByText('Use at least one letter or number.').length).toBeGreaterThan(0);

    await user.clear(firstQuestion);
    await user.type(firstQuestion, 'Straße?');
    questionApi.confirm.mockRejectedValue(
      new questionApi.QuestionTransitionError(
        'Questions must be unique.',
        'question_review_invalid',
        { 'items.0.text': ['Enter a unique question.'] },
      ),
    );
    await user.click(screen.getByRole('button', { name: 'Confirm questions' }));

    expect((await screen.findAllByText('Enter a unique question.')).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Confirm questions' })).toBeDisabled();
  });

  it('stops appending questions at the 15-question limit', async () => {
    const user = userEvent.setup();
    renderApp('/tests/questions-ready');

    const addButton = await screen.findByRole('button', { name: 'Add question' });
    for (let number = 10; number <= 15; number += 1) {
      await user.click(addButton);
      const dialog = screen.getByRole('dialog');
      await user.click(within(dialog).getByRole('radio', { name: 'Write manually' }));
      await user.type(within(dialog).getByRole('textbox', { name: 'Question' }), `Extra ${number}`);
      await user.click(within(dialog).getByRole('button', { name: 'Add question' }));
    }

    expect(screen.getAllByRole('textbox')).toHaveLength(15);
    expect(addButton).toHaveAttribute('aria-disabled', 'true');
    await user.click(addButton);
    expect(screen.getAllByRole('textbox')).toHaveLength(15);
  });

  it('states exactly what Start over preserves and removes', async () => {
    const user = userEvent.setup();
    renderApp('/tests/upload-ready');
    await screen.findByRole('heading', { name: 'Upload manual' });
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
    expect(screen.getByRole('textbox', { name: 'Question 1' })).toHaveValue(
      'How do I complete the initial setup? (1)',
    );
    expect(screen.getByRole('button', { name: 'Generate again' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Confirm questions' })).toBeDisabled();
  });

  it('recovers from a failed confirmation without losing the draft', async () => {
    const user = userEvent.setup();
    questionApi.confirm.mockRejectedValue(new Error('network unavailable'));
    renderApp('/tests/questions-ready');

    const firstQuestion = await screen.findByRole('textbox', { name: 'Question 1' });
    await user.clear(firstQuestion);
    await user.type(firstQuestion, 'My edited question');
    await user.click(screen.getByRole('button', { name: 'Confirm questions' }));

    expect(await screen.findByText(/question action could not be completed/i)).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Question 1' })).toHaveValue('My edited question');
    expect(screen.getByRole('button', { name: 'Confirm questions' })).toBeEnabled();
  });

  it('keeps local edits when regeneration fails', async () => {
    const user = userEvent.setup();
    questionApi.generate.mockRejectedValue(new Error('network unavailable'));
    renderApp('/tests/questions-ready');

    const firstQuestion = await screen.findByRole('textbox', { name: 'Question 1' });
    await user.clear(firstQuestion);
    await user.type(firstQuestion, 'Keep this local edit');
    await user.click(screen.getByRole('button', { name: 'Generate again' }));
    await user.click(screen.getByRole('button', { name: 'Generate another draft' }));

    expect(await screen.findByText(/question action could not be completed/i)).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Question 1' })).toHaveValue('Keep this local edit');
  });

  it('keeps local edits while asynchronous regeneration still has the same draft', async () => {
    const user = userEvent.setup();
    const generating = getWorkspaceFixture('questions-ready');
    if (!generating) throw new Error('Missing questions-ready fixture');
    generating.status = 'generating';
    questionApi.generate.mockResolvedValue(generating);
    renderApp('/tests/questions-ready');

    const firstQuestion = await screen.findByRole('textbox', { name: 'Question 1' });
    await user.clear(firstQuestion);
    await user.type(firstQuestion, 'Keep this edit until a new set arrives');
    await user.click(screen.getByRole('button', { name: 'Generate again' }));
    await user.click(screen.getByRole('button', { name: 'Generate another draft' }));

    expect(await screen.findByRole('progressbar', { name: 'Generating questions' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Question 1' })).toHaveValue(
      'Keep this edit until a new set arrives',
    );
  });

  it('replaces local edits after successful regeneration', async () => {
    const user = userEvent.setup();
    const regenerated = getWorkspaceFixture('questions-ready');
    if (!regenerated?.questionSet) throw new Error('Missing questions-ready fixture');
    regenerated.questionSet.id = 'question-set-2';
    regenerated.questionSet.items[0].text = 'What changed in the regenerated draft?';
    regenerated.questions = regenerated.questionSet.items;
    questionApi.generate.mockResolvedValue(regenerated);
    renderApp('/tests/questions-ready');

    const firstQuestion = await screen.findByRole('textbox', { name: 'Question 1' });
    await user.clear(firstQuestion);
    await user.type(firstQuestion, 'Discard this edit after success');
    await user.click(screen.getByRole('button', { name: 'Generate again' }));
    await user.click(screen.getByRole('button', { name: 'Generate another draft' }));

    expect(await screen.findByRole('textbox', { name: 'Question 1' })).toHaveValue(
      'What changed in the regenerated draft?',
    );
  });

  it('keeps confirmed questions read-only', async () => {
    renderApp('/tests/upload-ready');
    await screen.findByRole('heading', { name: 'Upload manual' });
    await userEvent.setup().click(
      screen.getByRole('button', { name: 'Review and confirm questionsComplete' }),
    );

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.getByText('How do I complete the initial setup? (1)')).toBeInTheDocument();
  });
});
