import { describe, expect, it } from 'vitest';

import { getWorkspaceFixture } from '../../mocks/workspaces';
import { getStageState } from './stage-state';

describe('getStageState', () => {
  it('locks future stages and completes earlier stages', () => {
    const workspace = getWorkspaceFixture('questions-ready');
    expect(workspace).toBeDefined();
    if (!workspace) return;

    expect(getStageState(workspace, 'configuration')).toBe('complete');
    expect(getStageState(workspace, 'questions')).toBe('active');
    expect(getStageState(workspace, 'upload')).toBe('locked');
    expect(getStageState(workspace, 'evaluation')).toBe('locked');
  });

  it('marks an active evaluation as working', () => {
    const workspace = getWorkspaceFixture('evaluating');
    expect(workspace).toBeDefined();
    if (!workspace) return;
    expect(getStageState(workspace, 'evaluation')).toBe('working');
  });

  it('marks Review as working and Product setup as complete during initial generation', () => {
    const workspace = getWorkspaceFixture('configuration-generating');
    expect(workspace).toBeDefined();
    if (!workspace) return;

    expect(getStageState(workspace, 'configuration')).toBe('complete');
    expect(getStageState(workspace, 'questions')).toBe('working');
  });

  it('marks Upload manual as working during a replacement without regressing the workflow', () => {
    const workspace = getWorkspaceFixture('report-ready');
    expect(workspace).toBeDefined();
    if (!workspace) return;
    workspace.manualUpload = {
      id: 'pending-manual',
      filename: 'replacement.pdf',
      status: 'checking',
    };

    expect(getStageState(workspace, 'upload')).toBe('working');
    expect(workspace.currentStage).toBe('report');
  });
});
