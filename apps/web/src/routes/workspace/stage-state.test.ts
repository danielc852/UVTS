import { describe, expect, it } from 'vitest';

import { getWorkspaceFixture } from '../../api/fixtures/workspaces';
import { getStageState } from './stage-state';

describe('getStageState', () => {
  it('locks future stages and completes earlier stages', () => {
    const workspace = getWorkspaceFixture('questions-ready');
    expect(workspace).toBeDefined();
    if (!workspace) return;

    expect(getStageState(workspace, 'upload')).toBe('complete');
    expect(getStageState(workspace, 'questions')).toBe('active');
    expect(getStageState(workspace, 'evaluation')).toBe('locked');
  });

  it('marks an active evaluation as working', () => {
    const workspace = getWorkspaceFixture('evaluating');
    expect(workspace).toBeDefined();
    if (!workspace) return;
    expect(getStageState(workspace, 'evaluation')).toBe('working');
  });
});
