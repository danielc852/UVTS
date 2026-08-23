import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { renderApp } from '../../test/render-app';

describe('WorkspacePage', () => {
  it('renders only the current step in a clean workspace', async () => {
    renderApp('/');

    expect(await screen.findByRole('heading', { name: 'Check a manual' })).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(1);
    expect(screen.getByRole('heading', { name: '1. Upload manual' })).toBeInTheDocument();
    expect(screen.queryByText('Upload a manual to continue.')).not.toBeInTheDocument();
    expect(screen.getAllByRole('main')).toHaveLength(1);
  });

  it('lets the user go back to completed steps and return to the current step', async () => {
    const user = userEvent.setup();
    renderApp('/tests/questions-ready');

    expect(await screen.findByRole('heading', { name: '3. Review questions' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Back to Questions' }));
    expect(await screen.findByRole('heading', { name: '2. Generate questions' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '3. Review questions' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Continue to Review' }));
    expect(screen.getByRole('heading', { name: '3. Review questions' })).toBeInTheDocument();
  });

  it('restores a completed report route', async () => {
    renderApp('/tests/report-ready');

    expect(await screen.findByText('7 questions are covered out of 9 total questions.')).toBeInTheDocument();
    expect(screen.getAllByText('Information partly found').length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'Main gaps' })).toBeInTheDocument();
  });

  it('shows a persistent plain-language upload error fixture', async () => {
    renderApp('/tests/upload-error');

    expect(await screen.findByText('The manual was not added')).toBeInTheDocument();
    expect(screen.getByText(/Scanned documents are not supported yet/)).toBeInTheDocument();
  });

  it('marks an incomplete report and offers a retry', async () => {
    renderApp('/tests/incomplete-report');

    expect(await screen.findByText('Report incomplete')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Retry failed questions' }).length).toBeGreaterThan(0);
  });
});
