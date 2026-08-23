import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderApp } from '../../test/render-app';

describe('WorkspacePage', () => {
  it('renders a clean five-stage workspace with one main landmark', async () => {
    renderApp('/');

    expect(await screen.findByRole('heading', { name: 'Check a manual' })).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(5);
    expect(screen.getByText('Upload a manual to continue.')).toBeInTheDocument();
    expect(screen.getAllByRole('main')).toHaveLength(1);
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
