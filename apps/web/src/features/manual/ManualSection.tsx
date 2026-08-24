import { AlertDialog } from '@astryxdesign/core/AlertDialog';
import { Banner } from '@astryxdesign/core/Banner';
import { Button } from '@astryxdesign/core/Button';
import { FileInput } from '@astryxdesign/core/FileInput';
import { ProgressBar } from '@astryxdesign/core/ProgressBar';
import { useQueryClient } from '@tanstack/react-query';
import { lazy, Suspense, useState } from 'react';

import {
  deleteManual,
  DocumentRequestError,
  manualContentUrl,
  uploadManual,
} from '../../api/documents';
import { queryKeys } from '../../api/query-keys';
import type { TestWorkspace } from '../../shared/model/workspace';
import { StageSection } from '../../shared/ui/StageSection';

const PdfViewer = lazy(() =>
  import('./PdfViewer').then((module) => ({ default: module.PdfViewer })),
);

interface ManualSectionProps {
  workspace: TestWorkspace;
  state?: 'locked' | 'active' | 'working' | 'complete';
}

type Confirmation = 'replace' | 'remove';

function isPdf(file: File): boolean {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
}

export function ManualSection({ workspace, state = 'active' }: ManualSectionProps) {
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fileError, setFileError] = useState<string>();
  const [actionError, setActionError] = useState<string>();
  const [confirmation, setConfirmation] = useState<Confirmation>();
  const manual = workspace.manual;
  const testId = workspace.id;
  const isBusy = isSubmitting || Boolean(workspace.manualUpload);

  if (state === 'locked') {
    return (
      <StageSection
        number={3}
        title="Upload manual"
        state="locked"
        lockedText="Confirm the question set before uploading a manual."
      />
    );
  }

  const storeWorkspace = (updated: TestWorkspace) => {
    queryClient.setQueryData(queryKeys.test(updated.id), updated);
  };

  const submitFile = async (file: File): Promise<boolean> => {
    setIsSubmitting(true);
    setActionError(undefined);
    setUploadProgress(0);
    try {
      const updated = await uploadManual({ file, testId, onProgress: setUploadProgress });
      storeWorkspace(updated);
      if (updated.error?.stage === 'upload') {
        return false;
      }
      setSelectedFile(null);
      return true;
    } catch (error) {
      setActionError(
        error instanceof DocumentRequestError
          ? error.message
          : 'The manual could not be uploaded. Try again.',
      );
      return false;
    } finally {
      setIsSubmitting(false);
      setUploadProgress(undefined);
    }
  };

  const handleFileChange = (value: File | File[] | null) => {
    const file = value instanceof File ? value : Array.isArray(value) ? (value[0] ?? null) : null;
    setSelectedFile(file);
    setFileError(undefined);
    setActionError(undefined);
    if (!file) return;
    if (!isPdf(file)) {
      setFileError('Upload a PDF file.');
      return;
    }
    if (manual) {
      setConfirmation('replace');
      return;
    }
    void submitFile(file);
  };

  const remove = async () => {
    setIsSubmitting(true);
    setActionError(undefined);
    try {
      const updated = await deleteManual(testId);
      storeWorkspace(updated);
      setConfirmation(undefined);
    } catch (error) {
      setActionError(
        error instanceof DocumentRequestError
          ? error.message
          : 'The manual could not be removed. Try again.',
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const confirm = async () => {
    if (confirmation === 'replace' && selectedFile) {
      if (await submitFile(selectedFile)) setConfirmation(undefined);
    } else if (confirmation === 'remove') {
      await remove();
    }
  };

  const progressLabel = workspace.manualUpload
    ? workspace.manualUpload.status === 'checking'
      ? `Checking ${workspace.manualUpload.filename}`
      : `Preparing ${workspace.manualUpload.filename}`
    : 'Uploading manual';

  return (
    <StageSection
      number={3}
      title="Upload manual"
      state={state}
      summary={manual ? `${manual.filename} · ${manual.pageCount} pages · Ready` : undefined}
      error={workspace.error}
    >
      <p>Upload one readable PDF with 1–20 pages. Password-protected and scanned PDFs are not supported.</p>
      {actionError ? (
        <Banner status="error" title="The manual was not added" description={actionError} />
      ) : null}
      {workspace.manualUpload ? (
        <Banner
          status="info"
          title={workspace.manualUpload.status === 'checking' ? 'Checking the PDF' : 'Preparing the manual'}
          description={
            manual
              ? 'Your current manual stays available until the replacement is ready.'
              : 'UVTS is confirming the page count and readable text.'
          }
        />
      ) : null}
      {isSubmitting && uploadProgress !== undefined ? (
        <div className="manual-progress">
          <ProgressBar label="Uploading manual" value={uploadProgress} hasValueLabel />
        </div>
      ) : workspace.manualUpload ? (
        <div className="manual-progress">
          <ProgressBar label={progressLabel} isIndeterminate />
        </div>
      ) : null}

      {manual ? (
        <div className="manual-ready" aria-live="polite">
          <div className="manual-ready-heading">
            <div>
              <strong>{manual.filename}</strong>
              <p className="supporting-text">{manual.pageCount} pages · Ready</p>
            </div>
            <div className="manual-actions">
              <a
                className="document-link"
                href={manualContentUrl(testId)}
                target="_blank"
                rel="noreferrer"
              >
                Open original PDF
              </a>
              <Button
                label="Remove manual"
                variant="ghost"
                isDisabled={isBusy}
                onClick={() => {
                  setConfirmation('remove');
                }}
              />
            </div>
          </div>
          <Suspense fallback={<p role="status">Loading document viewer…</p>}>
            <PdfViewer
              key={manual.id}
              filename={manual.filename}
              url={manualContentUrl(testId)}
            />
          </Suspense>
        </div>
      ) : null}

      <div className="manual-file-input">
        <FileInput
          label={manual ? 'Replace the PDF manual' : 'Upload a PDF manual'}
          description="One readable PDF, 1–20 pages."
          accept="application/pdf,.pdf"
          mode="dropzone"
          value={selectedFile}
          onChange={handleFileChange}
          isDisabled={isBusy}
          disabledMessage="Wait for the current upload and PDF check to finish."
          isLoading={isBusy}
          status={fileError ? { type: 'error', message: fileError } : undefined}
          statusVariant="detached"
          width="100%"
        />
      </div>

      <AlertDialog
        isOpen={Boolean(confirmation)}
        onOpenChange={(isOpen) => {
          if (!isOpen && !isSubmitting) {
            setConfirmation(undefined);
            if (confirmation === 'replace') setSelectedFile(null);
          }
        }}
        title={confirmation === 'replace' ? 'Replace this manual?' : 'Remove this manual?'}
        description={
          confirmation === 'replace'
            ? 'Confirmed questions and Product setup will remain. When the replacement is ready, evaluation and report data from this manual will be permanently removed.'
            : 'Product setup and confirmed questions will remain. The manual, evaluation, and report will be permanently removed.'
        }
        actionLabel={confirmation === 'replace' ? 'Replace manual' : 'Remove manual and results'}
        cancelLabel="Cancel"
        isActionLoading={isSubmitting}
        onAction={() => void confirm()}
      />
    </StageSection>
  );
}
