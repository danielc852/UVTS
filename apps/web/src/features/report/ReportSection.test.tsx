import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { renderApp } from '../../test/render-app';

describe('ReportSection', () => {
  it('presents the report as an accessible coverage dashboard', async () => {
    renderApp('/tests/report-ready');

    expect(await screen.findByRole('heading', { name: 'Test summary' })).toBeInTheDocument();
    expect(screen.getByText('7 questions are covered out of 9 total questions.')).toBeInTheDocument();

    const chart = screen.getByRole('group', { name: 'Coverage breakdown' });
    expect(
      within(chart).getByRole('button', {
        name: 'Information found: 7 of 9. Show matching results.',
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole('radiogroup', { name: 'Filter question results' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'All 9' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByText('Showing 9 of 9 question results.')).toBeInTheDocument();
  });

  it('filters question results from the controls and coverage chart', async () => {
    const user = userEvent.setup();
    renderApp('/tests/report-ready');
    await screen.findByRole('heading', { name: 'Question results' });

    await user.click(screen.getByRole('radio', { name: 'Review 2' }));
    expect(screen.getByText('Showing 2 of 9 question results.')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /1\. How do I complete the initial setup/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /8\. Can I change the export format/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /9\. What should I do if setup stops/ })).toBeInTheDocument();

    await user.click(
      screen.getByRole('button', {
        name: 'Information found: 7 of 9. Show matching results.',
      }),
    );
    expect(screen.getByRole('radio', { name: 'Found 7' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByText('Showing 7 of 9 question results.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /1\. How do I complete the initial setup/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /8\. Can I change the export format/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: 'Failed 0' }));
    expect(screen.getByText('No questions match this filter.')).toBeInTheDocument();
  });

  it('opens and focuses a question linked from a report gap', async () => {
    const user = userEvent.setup();
    renderApp('/tests/report-ready');
    await screen.findByRole('heading', { name: 'Main gaps' });

    await user.click(screen.getByRole('radio', { name: 'Found 7' }));
    expect(screen.queryByRole('button', { name: /8\. Can I change the export format/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Question 8' }));
    const linkedQuestion = await screen.findByRole('button', {
      name: /8\. Can I change the export format/,
    });
    await waitFor(() => {
      expect(linkedQuestion).toHaveAttribute('aria-expanded', 'true');
      expect(linkedQuestion).toHaveFocus();
    });
    expect(screen.getByRole('radio', { name: 'All 9' })).toHaveAttribute('aria-checked', 'true');
  });
});
