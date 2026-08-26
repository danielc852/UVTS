import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { renderApp } from '../../test/render-app';

describe('WorkspacePage', () => {
  it('renders only the current step in a clean workspace', async () => {
    renderApp('/');

    expect(await screen.findByRole('heading', { name: 'Check a manual' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Product setup' })).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(1);
    expect(screen.getAllByRole('main')).toHaveLength(1);
  });

  it('does not let stale route state unlock manual upload before confirmation', async () => {
    renderApp({ pathname: '/', state: { showUpload: true } });

    expect(await screen.findByRole('heading', { name: 'Product setup' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Upload manual' })).not.toBeInTheDocument();
  });

  it('lets the user go back to completed steps and return to the current step', async () => {
    const user = userEvent.setup();
    renderApp('/tests/questions-ready');

    expect(await screen.findByRole('heading', { name: 'Review and confirm questions' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Back to Product setup' }));
    expect(await screen.findByRole('heading', { name: 'Product setup' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Review and confirm questions' })).not.toBeInTheDocument();

    await user.click(
      screen.getByRole('button', { name: 'Continue to Review and confirm questions' }),
    );
    expect(screen.getByRole('heading', { name: 'Review and confirm questions' })).toBeInTheDocument();
  });

  it('restores a completed report route', async () => {
    renderApp('/tests/report-ready');

    expect(await screen.findByText('7 questions are covered out of 9 total questions.')).toBeInTheDocument();
    expect(screen.getAllByText('Information partly found').length).toBeGreaterThan(0);
    expect(screen.getByRole('heading', { name: 'Main gaps' })).toBeInTheDocument();
  });

  it('shows report generation after every question finishes without row retry buttons', async () => {
    renderApp('/tests/report-generating');

    expect(await screen.findByText('All questions have been checked. Generating the report…')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Generating report' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Retry question/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Retry failed questions' })).not.toBeInTheDocument();
  });

  it('shows confirmed Product setup as immutable when revisited', async () => {
    const user = userEvent.setup();
    renderApp('/tests/upload-ready');
    await screen.findByRole('heading', { name: 'Upload manual' });

    await user.click(screen.getByRole('button', { name: 'Product setupComplete' }));

    expect(await screen.findByText('Product setup locked')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Save and generate questions' })).not.toBeInTheDocument();
  });

  it('shows a persistent plain-language upload error fixture', async () => {
    renderApp('/tests/upload-error');

    expect(await screen.findByText('The manual was not added')).toBeInTheDocument();
    expect(screen.getByText(/Scanned documents are not supported yet/)).toBeInTheDocument();
  });

  it('marks an incomplete report and offers a retry', async () => {
    renderApp('/tests/incomplete-report');

    expect(await screen.findByText('Report incomplete')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry report' })).toBeInTheDocument();
  });
});
