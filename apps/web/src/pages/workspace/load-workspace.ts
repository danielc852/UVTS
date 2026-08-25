import { getTestWorkspace } from '../../entities/workspace/api';
import type { TestWorkspace } from '../../entities/workspace/model';
import { isMockWorkspaceId } from '../../mocks/workspace-ids';

export async function loadWorkspace(testId: string): Promise<TestWorkspace> {
  if (isMockWorkspaceId(testId)) {
    const { getWorkspaceFixture } = await import('../../mocks/workspaces');
    const fixture = getWorkspaceFixture(testId);
    if (fixture) return fixture;
  }

  return getTestWorkspace(testId);
}
