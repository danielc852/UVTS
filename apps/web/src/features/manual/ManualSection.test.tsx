import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getWorkspaceFixture } from '../../mocks/workspaces';
import { renderApp } from '../../test/render-app';

const documentApi = vi.hoisted(() => ({
  deleteManual: vi.fn(),
  uploadManual: vi.fn(),
}));

vi.mock('./api', () => ({
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

  it('attaches a PDF to the confirmed test and advances to Evaluation', async () => {
    const user = userEvent.setup();
    const ready = getWorkspaceFixture('upload-ready');
    expect(ready).toBeDefined();
    if (!ready) return;
    let finishUpload: ((workspace: typeof ready) => void) | undefined;
    documentApi.uploadManual.mockImplementation(({ onProgress }) => {
      onProgress?.(42);
      return new Promise((resolve) => {
        finishUpload = resolve;
      });
    });
    renderApp('/tests/upload-ready');

    await screen.findByRole('heading', { name: '3. Upload manual' });
    await user.upload(fileInput(), new File(['%PDF-test'], 'uploaded.pdf', { type: 'application/pdf' }));
    expect(await screen.findByRole('progressbar')).toHaveAttribute('aria-valuenow', '42');
    finishUpload?.({
      ...ready,
      status: 'ready',
      currentStage: 'evaluation',
      manual: {
        id: 'manual-2',
        filename: 'uploaded.pdf',
        pageCount: 4,
        status: 'ready',
      },
    });

    expect(await screen.findByRole('heading', { name: '4. Evaluation' })).toBeInTheDocument();
    expect(documentApi.uploadManual).toHaveBeenCalledWith(
      expect.objectContaining({ testId: 'upload-ready' }),
    );
  });

  it('confirms removing a manual that has connected results', async () => {
    const user = userEvent.setup();
    renderApp('/tests/report-ready');
    await screen.findByRole('heading', { name: '5. Report' });

    await user.click(screen.getByRole('button', { name: 'Upload manualComplete' }));
    await user.click(await screen.findByRole('button', { name: 'Remove manual' }));

    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Remove this manual?' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Remove manual and results' })).toBeInTheDocument();
  });

  it('removes only the manual-linked lineage and returns to Upload manual', async () => {
    const user = userEvent.setup();
    const uploadReady = getWorkspaceFixture('upload-ready');
    expect(uploadReady).toBeDefined();
    if (!uploadReady) return;
    documentApi.deleteManual.mockResolvedValue({ ...uploadReady, id: 'report-ready' });
    renderApp('/tests/report-ready');
    await screen.findByRole('heading', { name: '5. Report' });
    await user.click(screen.getByRole('button', { name: 'Upload manualComplete' }));
    await user.click(await screen.findByRole('button', { name: 'Remove manual' }));
    await user.click(screen.getByRole('button', { name: 'Remove manual and results' }));

    expect(await screen.findByRole('heading', { name: '3. Upload manual' })).toBeInTheDocument();
    expect(screen.queryByText('sample-product-manual.pdf', { selector: 'strong' })).not.toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(documentApi.deleteManual).toHaveBeenCalledWith('report-ready');
  });

  it('confirms replacing a manual that has connected results', async () => {
    const user = userEvent.setup();
    renderApp('/tests/report-ready');
    await screen.findByRole('heading', { name: '5. Report' });
    await user.click(screen.getByRole('button', { name: 'Upload manualComplete' }));

    await user.upload(fileInput(), new File(['%PDF-new'], 'replacement.pdf', { type: 'application/pdf' }));

    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Replace this manual?' })).toBeInTheDocument();
    expect(screen.getByText(/Confirmed questions and Product setup will remain/)).toBeInTheDocument();
  });

  it('keeps the old manual visible when starting a replacement fails', async () => {
    const user = userEvent.setup();
    documentApi.uploadManual.mockRejectedValue(new Error('network unavailable'));
    renderApp('/tests/report-ready');
    await screen.findByRole('heading', { name: '5. Report' });
    await user.click(screen.getByRole('button', { name: 'Upload manualComplete' }));
    await user.upload(fileInput(), new File(['%PDF-new'], 'replacement.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: 'Replace manual' }));

    expect(await screen.findByText('The manual could not be uploaded. Try again.')).toBeInTheDocument();
    expect(screen.getByText('sample-product-manual.pdf', { selector: 'strong' })).toBeInTheDocument();
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
  });

  it('stays on Upload manual when eager validation returns a preserved-workspace error', async () => {
    const user = userEvent.setup();
    const reportReady = getWorkspaceFixture('report-ready');
    expect(reportReady).toBeDefined();
    if (!reportReady) return;
    documentApi.uploadManual.mockResolvedValue({
      ...reportReady,
      error: {
        code: 'manual_no_readable_text',
        stage: 'upload',
        title: 'The replacement was not added',
        message: 'The replacement PDF does not contain readable text.',
        retryable: false,
      },
    });
    renderApp('/tests/report-ready');
    await screen.findByRole('heading', { name: '5. Report' });
    await user.click(screen.getByRole('button', { name: 'Upload manualComplete' }));
    await user.upload(
      fileInput(),
      new File(['%PDF-new'], 'replacement.pdf', { type: 'application/pdf' }),
    );
    await user.click(screen.getByRole('button', { name: 'Replace manual' }));

    expect(await screen.findByRole('heading', { name: '3. Upload manual' })).toBeInTheDocument();
    expect(screen.getByText('The replacement PDF does not contain readable text.')).toBeInTheDocument();
    expect(screen.getByText('sample-product-manual.pdf', { selector: 'strong' })).toBeInTheDocument();
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '5. Report' })).not.toBeInTheDocument();
  });

  it('stays on Upload manual while a background replacement is checked', async () => {
    const user = userEvent.setup();
    const reportReady = getWorkspaceFixture('report-ready');
    expect(reportReady).toBeDefined();
    if (!reportReady) return;
    documentApi.uploadManual.mockResolvedValue({
      ...reportReady,
      manualUpload: {
        id: 'pending-manual',
        filename: 'replacement.pdf',
        status: 'checking',
      },
    });
    renderApp('/tests/report-ready');
    await screen.findByRole('heading', { name: '5. Report' });
    await user.click(screen.getByRole('button', { name: 'Upload manualComplete' }));
    await user.upload(
      fileInput(),
      new File(['%PDF-new'], 'replacement.pdf', { type: 'application/pdf' }),
    );
    await user.click(screen.getByRole('button', { name: 'Replace manual' }));

    expect(await screen.findByRole('heading', { name: '3. Upload manual' })).toBeInTheDocument();
    expect(screen.getByText('Checking the PDF')).toBeInTheDocument();
    expect(screen.getByText('sample-product-manual.pdf', { selector: 'strong' })).toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });
});
