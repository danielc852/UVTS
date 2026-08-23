import { FileInput } from '@astryxdesign/core/FileInput';
import { useState } from 'react';

import type { ManualSummary, WorkspaceError } from '../../shared/model/workspace';
import { StageSection } from '../../shared/ui/StageSection';

interface ManualSectionProps {
  manual?: ManualSummary;
  error?: WorkspaceError;
  state?: 'active' | 'complete';
}

export function ManualSection({ manual, error, state = manual ? 'complete' : 'active' }: ManualSectionProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  return (
    <StageSection
      number={1}
      title="Upload manual"
      state={state}
      summary={manual ? `${manual.filename} · ${manual.pageCount} pages · Ready` : undefined}
      error={error}
    >
      <p>Upload one readable PDF with 1–20 pages. Password-protected and scanned PDFs are not supported.</p>
      <FileInput
        label="Upload a PDF manual"
        description="One readable PDF, 1–20 pages."
        accept="application/pdf,.pdf"
        mode="dropzone"
        value={selectedFile}
        onChange={(value) => setSelectedFile(value as File | null)}
        width="100%"
      />
      {selectedFile ? (
        <p className="supporting-text" role="status">
          Mock selection: {selectedFile.name}. Upload handling will connect to the FastAPI contract.
        </p>
      ) : null}
    </StageSection>
  );
}
