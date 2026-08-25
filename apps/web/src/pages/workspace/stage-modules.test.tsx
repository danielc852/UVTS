import { waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

const reportModuleLoaded = vi.hoisted(() => vi.fn());

vi.mock('../../features/report/ReportSection', () => {
  reportModuleLoaded();
  return { ReportSection: () => null };
});

describe('workspace stage modules', () => {
  it('preloads a requested stage through its static module loader', async () => {
    const { preloadWorkspaceStage } = await import('./stage-modules');

    expect(reportModuleLoaded).not.toHaveBeenCalled();
    preloadWorkspaceStage('report');

    await waitFor(() => expect(reportModuleLoaded).toHaveBeenCalledOnce());
  });
});
