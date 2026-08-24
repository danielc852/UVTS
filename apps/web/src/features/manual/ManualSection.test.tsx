import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from '../../api/fixtures/workspaces';
import { renderApp } from '../../test/render-app';

const documentApi = vi.hoisted(() => ({
  deleteManual: vi.fn(),
  uploadManual: vi.fn(),
}));

vi.mock('../../api/documents', () => ({
  deleteManual: documentApi.deleteManual,
  DocumentRequestError: class DocumentRequestError extends Error {},
  manualContentUrl: (testId: string) => `/api/v1/tests/${testId}/manual/content`,
  uploadManual: documentApi.uploadManual,
}));

vi.mock('./PdfViewer', () => ({
  PdfViewer: ({ filename }: { filename: string }) => <div>Previewing {filename}</div>,
}));

function fileInput(): HTMLInputElement {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error('File input not found');
  return input;
}

describe('ManualSection', () => {
  beforeEach(() => {
    documentApi.deleteManual.mockReset();
    documentApi.uploadManual.mockReset();
  });

  it('uploads a PDF, stays on Upload, and shows the ready viewer', async () => {
    const user = userEvent.setup();
    const ready = getWorkspaceFixture('manual-ready');
    expect(ready).toBeDefined();
    if (!ready) return;
    let finishUpload: ((workspace: typeof ready) => void) | undefined;
    documentApi.uploadManual.mockImplementation(({ onProgress }) => {
      onProgress?.(42);
      return new Promise((resolve) => {
        finishUpload = resolve;
      });
    });
    renderApp('/');

    await screen.findByRole('heading', { name: '1. Upload manual' });
    await user.upload(fileInput(), new File(['%PDF-test'], 'uploaded.pdf', { type: 'application/pdf' }));
    expect(await screen.findByRole('progressbar')).toHaveAttribute('aria-valuenow', '42');
    finishUpload?.({
      ...ready,
      id: 'uploaded-test',
      manual: ready.manual ? { ...ready.manual, filename: 'uploaded.pdf' } : undefined,
    });

    expect(await screen.findByText('uploaded.pdf', { selector: 'strong' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '1. Upload manual' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open original PDF' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Continue to Questions' })).toBeInTheDocument();
  });

  it('confirms removing a manual that has connected results', async () => {
    const user = userEvent.setup();
    renderApp('/tests/report-ready');
    await screen.findByRole('heading', { name: '5. Report' });

    await user.click(screen.getByRole('button', { name: 'UploadComplete' }));
    await user.click(await screen.findByRole('button', { name: 'Remove manual' }));

    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Remove this manual?' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Remove manual and results' })).toBeInTheDocument();
  });

  it('confirms replacing a manual that has connected results', async () => {
    const user = userEvent.setup();
    renderApp('/tests/questions-ready');
    await screen.findByRole('heading', { name: '3. Review questions' });
    await user.click(screen.getByRole('button', { name: 'UploadComplete' }));

    await user.upload(fileInput(), new File(['%PDF-new'], 'replacement.pdf', { type: 'application/pdf' }));

    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Replace this manual?' })).toBeInTheDocument();
    expect(screen.getByText(/connected questions and results will be permanently removed/)).toBeInTheDocument();
  });

  it('keeps the old manual visible when starting a replacement fails', async () => {
    const user = userEvent.setup();
    documentApi.uploadManual.mockRejectedValue(new Error('network unavailable'));
    renderApp('/tests/questions-ready');
    await screen.findByRole('heading', { name: '3. Review questions' });
    await user.click(screen.getByRole('button', { name: 'UploadComplete' }));
    await user.upload(fileInput(), new File(['%PDF-new'], 'replacement.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: 'Replace manual' }));

    expect(await screen.findByText('The manual could not be uploaded. Try again.')).toBeInTheDocument();
    expect(screen.getByText('sample-product-manual.pdf', { selector: 'strong' })).toBeInTheDocument();
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
  });
});
